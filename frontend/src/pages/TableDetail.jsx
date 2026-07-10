// ==============================================================================
// File:      frontend/src/pages/TableDetail.jsx
// Purpose:   Table detail page. Shows table info, members, invite code (for DM),
//            characters grid, and session history filtered to this table.
// Callers:   App.jsx (route: /tables/:id)
// Callees:   React, react-router-dom, api/tables.js, api/history.js,
//            PageHeader.jsx, ContentCard.jsx
// Modified:  2026-06-01
// ==============================================================================
import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { getTable, regenerateCode, deleteTable, getTableCharacters, updateTable } from '../api/tables';
import { createCharacter, updateCharacter, uploadPortrait, claimCharacter, unclaimCharacter, deleteCharacter } from '../api/characters';
import { getNpcs, createNpc, updateNpc, deleteNpc } from '../api/npcs';
import { getSessions, getSessionScenes } from '../api/history';
import PageHeader from '../components/PageHeader';
import PageContent from '../components/PageContent';
import ContentCard from '../components/ContentCard';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5151';

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function TableDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);

  const [table, setTable] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // DM actions
  const [codeCopied, setCodeCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Player character management
  const [myCharacter, setMyCharacter] = useState(null);
  const [showCharForm, setShowCharForm] = useState(false);
  const [charForm, setCharForm] = useState({ name: '', description: '' });
  const [charLoading, setCharLoading] = useState(false);
  const [charError, setCharError] = useState(null);
  const [portraitFile, setPortraitFile] = useState(null);
  const [portraitPreview, setPortraitPreview] = useState(null);
  const [portraitUploading, setPortraitUploading] = useState(false);

  // DM-managed character flow (create unclaimed, edit any)
  const [dmForm, setDmForm] = useState({ open: false, charId: null, name: '', description: '' });
  const [dmFormBusy, setDmFormBusy] = useState(false);
  const [dmFormError, setDmFormError] = useState(null);
  const [claimingCharId, setClaimingCharId] = useState(null);
  const [unclaimingCharId, setUnclaimingCharId] = useState(null);
  const [unclaimConfirm, setUnclaimConfirm] = useState(null);

  // Character delete (DM only)
  const [charDeleteConfirm, setCharDeleteConfirm] = useState(null);
  const [charDeleting, setCharDeleting] = useState(false);

  // NPC management (DM only)
  const [npcs, setNpcs] = useState([]);
  const [npcForm, setNpcForm] = useState({ open: false, npcId: null, name: '', description: '' });
  const [npcFormBusy, setNpcFormBusy] = useState(false);
  const [npcFormError, setNpcFormError] = useState(null);
  const [npcDeleting, setNpcDeleting] = useState(null);

  // DM Notes (free-form scratchpad)
  const [notesDraft, setNotesDraft] = useState('');

  // Scene model picker — DM chooses which Claude model handles scene
  // extraction for sessions on this table. Empty string = system default.
  const [sceneModel, setSceneModel] = useState('');
  const [sceneModelSaving, setSceneModelSaving] = useState(false);
  const [notesSaving, setNotesSaving] = useState(false);
  const [notesSavedAt, setNotesSavedAt] = useState(null);

  // Session art gallery
  const [sessionScenes, setSessionScenes] = useState({});
  const [artLoading, setArtLoading] = useState(false);
  const [lightbox, setLightbox] = useState(null);

  const isOwner = table?.role === 'DM' || table?.role === 'owner' || table?.is_owner;
  const isPlayer = !isOwner;

  const fetchTable = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTable(id);
      setTable(data);
      setNotesDraft(data?.notes || '');
      setSceneModel(data?.scene_model || '');
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load table.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchNpcs = useCallback(async () => {
    try {
      const data = await getNpcs(id);
      setNpcs(data.npcs || []);
    } catch (_) {
      // Non-critical — NPCs section just renders empty
    }
  }, [id]);

  const fetchCharacters = useCallback(async () => {
    try {
      const data = await getTableCharacters(id);
      const charList = data.characters || data || [];
      setCharacters(charList);
      // Find the current user's character
      const mine = charList.find((c) => c.user_id === user?.id);
      if (mine) {
        setMyCharacter(mine);
        setCharForm({ name: mine.name, description: mine.description || '' });
      }
    } catch (_) {
      // Characters may not exist yet
    }
  }, [id, user?.id]);

  const fetchSessions = useCallback(async () => {
    setArtLoading(true);
    try {
      const data = await getSessions(1, 50);
      const allSessions = data.sessions || [];
      // Filter sessions by table_id
      const tableSessions = allSessions.filter(
        (s) => s.table_id === id || s.table_id === Number(id)
      );
      // Sort newest first
      tableSessions.sort(
        (a, b) => new Date(b.started_at || b.created_at) - new Date(a.started_at || a.created_at)
      );
      setSessions(tableSessions);

      // Fetch scenes for each session (for the art gallery)
      const scenesMap = {};
      await Promise.all(
        tableSessions.map(async (session) => {
          try {
            const sceneData = await getSessionScenes(session.id, 1, 50);
            scenesMap[session.id] = sceneData.scenes || [];
          } catch {
            scenesMap[session.id] = [];
          }
        })
      );
      setSessionScenes(scenesMap);
    } catch (_) {
      // Sessions fetch failure is non-critical
    } finally {
      setArtLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTable();
    fetchCharacters();
    fetchNpcs();
    fetchSessions();
  }, [fetchTable, fetchCharacters, fetchNpcs, fetchSessions]);

  const handleCopyCode = useCallback(() => {
    if (!table?.invite_code) return;
    navigator.clipboard.writeText(table.invite_code).then(() => {
      setCodeCopied(true);
      setTimeout(() => setCodeCopied(false), 2000);
    });
  }, [table]);

  const handleRegenerate = useCallback(async () => {
    setRegenerating(true);
    try {
      const data = await regenerateCode(id);
      setTable((prev) => ({ ...prev, invite_code: data.invite_code || data.code }));
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to regenerate code.');
    } finally {
      setRegenerating(false);
    }
  }, [id]);

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    try {
      await deleteTable(id);
      navigate('/tables');
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to delete table.');
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  }, [id, navigate]);

  // ---- Player character form ----
  const handleCharSubmit = useCallback(async (e) => {
    e.preventDefault();
    setCharLoading(true);
    setCharError(null);
    try {
      if (myCharacter) {
        const data = await updateCharacter(id, myCharacter.id, charForm);
        const updated = data.character || data;
        setMyCharacter(updated);
        setShowCharForm(false);
      } else {
        const data = await createCharacter(id, charForm);
        const created = data.character || data;
        setMyCharacter(created);
        setCharacters((prev) => [...prev, created]);
        setShowCharForm(false);
      }
    } catch (err) {
      setCharError(err.response?.data?.error || 'Failed to save character.');
    } finally {
      setCharLoading(false);
    }
  }, [id, myCharacter, charForm]);

  // ---- DM-managed characters ----
  const openDmCreate = useCallback(() => {
    setDmForm({ open: true, charId: null, name: '', description: '' });
    setDmFormError(null);
  }, []);

  const openDmEdit = useCallback((char) => {
    setDmForm({ open: true, charId: char.id, name: char.name, description: char.description || '' });
    setDmFormError(null);
  }, []);

  const closeDmForm = useCallback(() => {
    setDmForm({ open: false, charId: null, name: '', description: '' });
    setDmFormError(null);
  }, []);

  const handleDmSubmit = useCallback(async (e) => {
    e.preventDefault();
    setDmFormBusy(true);
    setDmFormError(null);
    try {
      if (dmForm.charId) {
        await updateCharacter(id, dmForm.charId, { name: dmForm.name, description: dmForm.description });
      } else {
        await createCharacter(id, { name: dmForm.name, description: dmForm.description, unclaimed: true });
      }
      await fetchCharacters();
      closeDmForm();
    } catch (err) {
      setDmFormError(err?.response?.data?.error || 'Failed to save character.');
    } finally {
      setDmFormBusy(false);
    }
  }, [id, dmForm, fetchCharacters, closeDmForm]);

  const handleClaim = useCallback(async (charId) => {
    setClaimingCharId(charId);
    try {
      await claimCharacter(id, charId);
      await fetchCharacters();
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to claim character.');
    } finally {
      setClaimingCharId(null);
    }
  }, [id, fetchCharacters]);

  // ---- Character delete (DM) ----
  const handleCharDelete = useCallback(async () => {
    if (!charDeleteConfirm) return;
    setCharDeleting(true);
    try {
      await deleteCharacter(id, charDeleteConfirm.id);
      await fetchCharacters();
      setCharDeleteConfirm(null);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to delete character.');
    } finally {
      setCharDeleting(false);
    }
  }, [id, charDeleteConfirm, fetchCharacters]);

  // ---- NPCs ----
  const openNpcCreate = useCallback(() => {
    setNpcForm({ open: true, npcId: null, name: '', description: '' });
    setNpcFormError(null);
  }, []);

  const openNpcEdit = useCallback((npc) => {
    setNpcForm({ open: true, npcId: npc.id, name: npc.name, description: npc.description || '' });
    setNpcFormError(null);
  }, []);

  const closeNpcForm = useCallback(() => {
    setNpcForm({ open: false, npcId: null, name: '', description: '' });
    setNpcFormError(null);
  }, []);

  const handleNpcSubmit = useCallback(async (e) => {
    e.preventDefault();
    setNpcFormBusy(true);
    setNpcFormError(null);
    try {
      if (npcForm.npcId) {
        await updateNpc(id, npcForm.npcId, { name: npcForm.name, description: npcForm.description });
      } else {
        await createNpc(id, { name: npcForm.name, description: npcForm.description });
      }
      await fetchNpcs();
      closeNpcForm();
    } catch (err) {
      setNpcFormError(err?.response?.data?.error || 'Failed to save NPC.');
    } finally {
      setNpcFormBusy(false);
    }
  }, [id, npcForm, fetchNpcs, closeNpcForm]);

  const handleNpcDelete = useCallback(async (npc) => {
    setNpcDeleting(npc.id);
    try {
      await deleteNpc(id, npc.id);
      await fetchNpcs();
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to delete NPC.');
    } finally {
      setNpcDeleting(null);
    }
  }, [id, fetchNpcs]);

  // ---- Notes ----
  const handleSaveSceneModel = useCallback(async (next) => {
    setSceneModel(next);
    setSceneModelSaving(true);
    try {
      await updateTable(id, { scene_model: next });
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to save model choice.');
    } finally {
      setSceneModelSaving(false);
    }
  }, [id]);

  const handleSaveNotes = useCallback(async () => {
    setNotesSaving(true);
    try {
      await updateTable(id, { notes: notesDraft });
      setNotesSavedAt(Date.now());
      setTimeout(() => setNotesSavedAt(null), 2000);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to save notes.');
    } finally {
      setNotesSaving(false);
    }
  }, [id, notesDraft]);

  const handleUnclaim = useCallback(async () => {
    if (!unclaimConfirm) return;
    const charId = unclaimConfirm.id;
    setUnclaimingCharId(charId);
    try {
      await unclaimCharacter(id, charId);
      await fetchCharacters();
      setUnclaimConfirm(null);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to release character.');
    } finally {
      setUnclaimingCharId(null);
    }
  }, [id, unclaimConfirm, fetchCharacters]);

  const handlePortraitSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPortraitFile(file);
    setPortraitPreview(URL.createObjectURL(file));
  }, []);

  const handlePortraitUpload = useCallback(async () => {
    if (!portraitFile || !myCharacter) return;
    setPortraitUploading(true);
    try {
      const data = await uploadPortrait(id, myCharacter.id, portraitFile);
      setMyCharacter((prev) => ({ ...prev, portrait_path: data.portrait_path || data.url }));
      setPortraitFile(null);
      setPortraitPreview(null);
    } catch {
      setCharError('Failed to upload portrait.');
    } finally {
      setPortraitUploading(false);
    }
  }, [id, myCharacter, portraitFile]);

  // ---- Lightbox ----
  const openLightbox = useCallback((scene) => setLightbox(scene), []);
  const closeLightbox = useCallback(() => setLightbox(null), []);

  useEffect(() => {
    if (!lightbox) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') closeLightbox();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [lightbox, closeLightbox]);

  if (loading) {
    return (
      <div className="table-detail-page">
        <p className="tables-loading">Loading table...</p>
      </div>
    );
  }

  if (!table && !loading) {
    return (
      <div className="table-detail-page">
        <div className="tables-error">{error || 'Table not found.'}</div>
      </div>
    );
  }

  return (
    <div className="table-detail-page">
      <PageHeader
        title={table.name}
        subtitle={isOwner ? 'Dungeon Master' : 'Player'}
      />

      <PageContent>
      {error && <div className="tables-error">{error}</div>}

      {/* DM Notes (DM only) — free-form world/lore scratchpad fed into the Claude prompt */}
      {isOwner && (
        <ContentCard className="table-detail__notes-section">
          <h3 className="table-detail__section-title">DM Notes</h3>
          <p className="table-detail__notes-hint">
            World state, lore, NPC names — anything Claude should treat as ground truth during scene generation.
          </p>
          <textarea
            className="form-input"
            value={notesDraft}
            onChange={(e) => setNotesDraft(e.target.value)}
            placeholder="e.g. The king's name is Mort. The party owes 200gp to the Thieves' Guild. Snow on the mountains."
            rows={4}
            style={notesTextarea}
          />
          <div style={notesActions}>
            <button
              className="btn btn--primary btn--small"
              onClick={handleSaveNotes}
              disabled={notesSaving || (notesDraft === (table.notes || ''))}
            >
              {notesSavedAt ? 'Saved!' : notesSaving ? 'Saving...' : 'Save Notes'}
            </button>
          </div>
        </ContentCard>
      )}

      {/* Invite Code (DM only) */}
      {isOwner && table.invite_code && (
        <ContentCard className="table-detail__invite-section">
          <h3 className="table-detail__section-title">Invite Code</h3>
          <p className="table-detail__invite-hint">
            Share this code with players so they can join your table.
          </p>
          <button
            className="table-detail__invite-code-btn"
            onClick={handleCopyCode}
          >
            <span className="table-detail__invite-code-text">
              {table.invite_code}
            </span>
            <span className="table-detail__invite-copy-label">
              {codeCopied ? 'Copied!' : 'Copy'}
            </span>
          </button>
          <div className="table-detail__invite-actions">
            <button
              className="btn btn--ghost btn--small"
              onClick={handleRegenerate}
              disabled={regenerating}
            >
              {regenerating ? 'Regenerating...' : 'Regenerate Code'}
            </button>
          </div>
        </ContentCard>
      )}

      {/* Members */}
      <ContentCard className="table-detail__members-section">
        <h3 className="table-detail__section-title">
          Members ({table.members?.length || 0})
        </h3>
        {table.members && table.members.length > 0 ? (
          <div className="table-detail__members-list">
            {table.members.map((member) => (
              <div key={member.id || member.user_id} className="table-detail__member">
                <span className="table-detail__member-name">
                  {member.username || member.name}
                </span>
                <span className={`table-detail__member-role table-detail__member-role--${(member.role || 'player').toLowerCase()}`}>
                  {member.role || 'Player'}
                </span>
                {member.character_name && (
                  <span className="table-detail__member-character">
                    as {member.character_name}
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted">No members yet.</p>
        )}
      </ContentCard>

      {/* Character Management (players and DMs) */}
      {(isPlayer || isOwner) && (
        <section className="character-section">
          <h2 className="section-title">Your Character</h2>

          {!myCharacter && !showCharForm && (
            <div className="character-empty">
              <p className="character-empty__text">
                You have not created a character for this table yet.
              </p>
              <button
                className="btn btn--primary"
                onClick={() => setShowCharForm(true)}
              >
                Create Your Character
              </button>
            </div>
          )}

          {myCharacter && !showCharForm && (
            <div className="character-card">
              {myCharacter.portrait_path && (
                <img
                  className="character-card__portrait"
                  src={myCharacter.portrait_path.startsWith('http') ? myCharacter.portrait_path : `${API_URL}${myCharacter.portrait_path}`}
                  alt={`${myCharacter.name} portrait`}
                />
              )}
              <div className="character-card__info">
                <h3 className="character-card__name">{myCharacter.name}</h3>
                {myCharacter.description && (
                  <p className="character-card__description">{myCharacter.description}</p>
                )}
              </div>
              <button
                className="btn btn--secondary btn--small"
                onClick={() => {
                  setCharForm({ name: myCharacter.name, description: myCharacter.description || '' });
                  setShowCharForm(true);
                }}
              >
                Edit
              </button>
            </div>
          )}

          {showCharForm && (
            <form className="character-form" onSubmit={handleCharSubmit}>
              {charError && <div className="form-error">{charError}</div>}

              <div className="form-group">
                <label className="form-label" htmlFor="char-name">Character Name</label>
                <input
                  id="char-name"
                  className="form-input"
                  type="text"
                  value={charForm.name}
                  onChange={(e) => setCharForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Enter character name"
                  required
                  disabled={charLoading}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="char-desc">Description</label>
                <textarea
                  id="char-desc"
                  className="form-input character-form__textarea"
                  value={charForm.description}
                  onChange={(e) => setCharForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Describe your character's appearance, armor, weapons, distinguishing features..."
                  rows={4}
                  disabled={charLoading}
                />
              </div>

              {myCharacter && (
                <div className="form-group">
                  <label className="form-label">Portrait</label>
                  <div className="character-form__portrait-upload">
                    {(portraitPreview || myCharacter.portrait_path) && (
                      <img
                        className="character-form__portrait-preview"
                        src={portraitPreview || (myCharacter.portrait_path.startsWith('http') ? myCharacter.portrait_path : `${API_URL}${myCharacter.portrait_path}`)}
                        alt="Portrait preview"
                      />
                    )}
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handlePortraitSelect}
                      disabled={portraitUploading}
                    />
                    {portraitFile && (
                      <button
                        type="button"
                        className="btn btn--primary btn--small"
                        onClick={handlePortraitUpload}
                        disabled={portraitUploading}
                      >
                        {portraitUploading ? 'Uploading...' : 'Upload Portrait'}
                      </button>
                    )}
                  </div>
                </div>
              )}

              <div className="character-form__actions">
                <button
                  type="submit"
                  className="btn btn--primary"
                  disabled={charLoading || !charForm.name.trim()}
                >
                  {charLoading ? 'Saving...' : myCharacter ? 'Save Changes' : 'Create Character'}
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => setShowCharForm(false)}
                  disabled={charLoading}
                >
                  Cancel
                </button>
                {myCharacter && (
                  <button
                    type="button"
                    className="btn btn--danger"
                    onClick={() => {
                      setShowCharForm(false);
                      setCharDeleteConfirm(myCharacter);
                    }}
                    disabled={charLoading}
                    style={{ marginLeft: 'auto' }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </form>
          )}
        </section>
      )}

      {/* Party Characters (visible to everyone; DM can pre-create / edit) */}
      <ContentCard className="table-detail__characters-section">
        <div style={charactersHeader}>
          <h3 className="table-detail__section-title" style={{ margin: 0 }}>Party Characters</h3>
          {isOwner && !dmForm.open && (
            <button className="btn btn--primary btn--small" onClick={openDmCreate}>
              + Add Character
            </button>
          )}
        </div>

        {isOwner && dmForm.open && (
          <form onSubmit={handleDmSubmit} style={dmFormStyle}>
            {dmFormError && <div className="form-error">{dmFormError}</div>}
            <div className="form-group">
              <label className="form-label">Character Name</label>
              <input
                className="form-input"
                type="text"
                value={dmForm.name}
                onChange={(e) => setDmForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Aragorn"
                required
                disabled={dmFormBusy}
                maxLength={100}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                className="form-input character-form__textarea"
                value={dmForm.description}
                onChange={(e) => setDmForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Appearance, armor, distinguishing features..."
                rows={3}
                disabled={dmFormBusy}
              />
            </div>
            <div className="character-form__actions">
              <button type="submit" className="btn btn--primary" disabled={dmFormBusy || !dmForm.name.trim()}>
                {dmFormBusy ? 'Saving...' : dmForm.charId ? 'Save Changes' : 'Create (Unclaimed)'}
              </button>
              <button type="button" className="btn btn--ghost" onClick={closeDmForm} disabled={dmFormBusy}>
                Cancel
              </button>
            </div>
            {!dmForm.charId && (
              <p style={dmFormHint}>
                Unclaimed characters live on the table without a player account. A player can claim later, or it can stay unclaimed forever.
              </p>
            )}
          </form>
        )}

        {characters.length === 0 ? (
          <p className="text-muted">No characters in this party yet.</p>
        ) : (
          <div className="table-detail__characters-grid">
            {characters.map((char) => {
              const isUnclaimed = !char.user_id;
              const canClaim = isUnclaimed && !myCharacter && !isOwner;
              const status = isUnclaimed
                ? 'Unclaimed'
                : `Claimed by ${char.claimed_by_username || 'player'}`;
              return (
                <div key={char.id} className="table-detail__character-card">
                  {char.portrait_path && (
                    <img
                      className="table-detail__character-portrait"
                      src={char.portrait_path.startsWith('http') ? char.portrait_path : `${API_URL}${char.portrait_path}`}
                      alt={char.name}
                      loading="lazy"
                    />
                  )}
                  <div className="table-detail__character-info">
                    <h4 className="table-detail__character-name">{char.name}</h4>
                    <span style={isUnclaimed ? statusUnclaimed : statusClaimed}>{status}</span>
                    {char.description && (
                      <p className="table-detail__character-desc">
                        {char.description}
                      </p>
                    )}
                    <div style={charActions}>
                      {canClaim && (
                        <button
                          className="btn btn--blue btn--small"
                          onClick={() => handleClaim(char.id)}
                          disabled={claimingCharId === char.id}
                        >
                          {claimingCharId === char.id ? 'Claiming...' : 'Claim this character'}
                        </button>
                      )}
                      {isOwner && (
                        <button
                          className="btn btn--secondary btn--small"
                          onClick={() => openDmEdit(char)}
                        >
                          Edit
                        </button>
                      )}
                      {isOwner && !isUnclaimed && (
                        <button
                          className="btn btn--ghost btn--small"
                          onClick={() => setUnclaimConfirm(char)}
                          disabled={unclaimingCharId === char.id}
                        >
                          Release
                        </button>
                      )}
                      {isOwner && (
                        <button
                          className="btn btn--danger btn--small"
                          onClick={() => setCharDeleteConfirm(char)}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </ContentCard>

      {/* NPCs (DM-managed; visible to all) */}
      <ContentCard className="table-detail__characters-section">
        <div style={charactersHeader}>
          <h3 className="table-detail__section-title" style={{ margin: 0 }}>NPCs</h3>
          {isOwner && !npcForm.open && (
            <button className="btn btn--primary btn--small" onClick={openNpcCreate}>
              + Add NPC
            </button>
          )}
        </div>

        {isOwner && npcForm.open && (
          <form onSubmit={handleNpcSubmit} style={dmFormStyle}>
            {npcFormError && <div className="form-error">{npcFormError}</div>}
            <div className="form-group">
              <label className="form-label">NPC Name</label>
              <input
                className="form-input"
                type="text"
                value={npcForm.name}
                onChange={(e) => setNpcForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. King Mort, Innkeeper Greta"
                required
                disabled={npcFormBusy}
                maxLength={100}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                className="form-input character-form__textarea"
                value={npcForm.description}
                onChange={(e) => setNpcForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Appearance, role, distinguishing features..."
                rows={3}
                disabled={npcFormBusy}
              />
            </div>
            <div className="character-form__actions">
              <button type="submit" className="btn btn--primary" disabled={npcFormBusy || !npcForm.name.trim()}>
                {npcFormBusy ? 'Saving...' : npcForm.npcId ? 'Save Changes' : 'Add NPC'}
              </button>
              <button type="button" className="btn btn--ghost" onClick={closeNpcForm} disabled={npcFormBusy}>
                Cancel
              </button>
            </div>
          </form>
        )}

        {npcs.length === 0 ? (
          <p className="text-muted">No NPCs on this table yet.</p>
        ) : (
          <div className="table-detail__characters-grid">
            {npcs.map((npc) => (
              <div key={npc.id} className="table-detail__character-card">
                <div className="table-detail__character-info">
                  <h4 className="table-detail__character-name">{npc.name}</h4>
                  {npc.description && (
                    <p className="table-detail__character-desc">{npc.description}</p>
                  )}
                  {isOwner && (
                    <div style={charActions}>
                      <button className="btn btn--secondary btn--small" onClick={() => openNpcEdit(npc)}>
                        Edit
                      </button>
                      <button
                        className="btn btn--danger btn--small"
                        onClick={() => handleNpcDelete(npc)}
                        disabled={npcDeleting === npc.id}
                      >
                        {npcDeleting === npc.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </ContentCard>

      {/* Session Art Gallery */}
      <section className="session-art-section">
        <h2 className="section-title">Session Art</h2>

        {artLoading && <p className="history-loading">Loading session art...</p>}

        {!artLoading && sessions.length === 0 && (
          <div className="empty-state">
            <p className="empty-state__text">
              No session art yet. Art will appear here after sessions are played.
            </p>
          </div>
        )}

        {!artLoading && sessions.map((session) => {
          const scenes = sessionScenes[session.id] || [];
          if (scenes.length === 0) return null;
          return (
            <div key={session.id} className="session-art-group">
              <h3 className="session-art-group__date">
                {formatDate(session.started_at || session.created_at)}
              </h3>
              <div className="session-art-grid">
                {scenes.map((scene, i) => (
                  <div
                    key={scene.id || i}
                    className="session-art-thumb"
                    onClick={() => openLightbox(scene)}
                  >
                    {scene.image_url && (
                      <img
                        className="session-art-thumb__image"
                        src={scene.image_url}
                        alt={scene.description || 'Scene'}
                        loading="lazy"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </section>

      {/* Delete Table (DM only) */}
      {isOwner && (
        <div className="table-detail__danger-zone">
          <button
            className="btn btn--danger"
            onClick={() => setShowDeleteConfirm(true)}
          >
            Delete Table
          </button>
        </div>
      )}
      </PageContent>

      {/* Lightbox */}
      {lightbox && (
        <div className="history-lightbox" onClick={closeLightbox}>
          <button
            className="history-lightbox__close"
            onClick={closeLightbox}
            aria-label="Close"
          >
            &times;
          </button>
          <div
            className="history-lightbox__card"
            onClick={(e) => e.stopPropagation()}
          >
            {lightbox.image_url && (
              <img
                className="history-lightbox__image"
                src={lightbox.image_url}
                alt={lightbox.description || 'Scene'}
              />
            )}
            {lightbox.description && (
              <div className="history-lightbox__body">
                <p className="history-lightbox__desc">{lightbox.description}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Character Delete Confirmation */}
      {charDeleteConfirm && (
        <div className="session-confirm-overlay" onClick={() => setCharDeleteConfirm(null)}>
          <div className="session-confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Delete Character?</h3>
            <p>
              Permanently delete &ldquo;{charDeleteConfirm.name}&rdquo; from this table? Their portrait and
              description go with them. This cannot be undone.
            </p>
            <div className="session-confirm-dialog__actions">
              <button className="btn btn--cancel" onClick={() => setCharDeleteConfirm(null)}>
                Cancel
              </button>
              <button className="btn btn--end" onClick={handleCharDelete} disabled={charDeleting}>
                {charDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Unclaim Confirmation */}
      {unclaimConfirm && (
        <div
          className="session-confirm-overlay"
          onClick={() => setUnclaimConfirm(null)}
        >
          <div
            className="session-confirm-dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>Release Character?</h3>
            <p>
              Release &ldquo;{unclaimConfirm.name}&rdquo; from {unclaimConfirm.claimed_by_username || 'this player'}? The
              character stays on the table as unclaimed and can be re-claimed by anyone.
            </p>
            <div className="session-confirm-dialog__actions">
              <button
                className="btn btn--cancel"
                onClick={() => setUnclaimConfirm(null)}
              >
                Cancel
              </button>
              <button
                className="btn btn--end"
                onClick={handleUnclaim}
                disabled={unclaimingCharId === unclaimConfirm.id}
              >
                {unclaimingCharId === unclaimConfirm.id ? 'Releasing...' : 'Release'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div
          className="session-confirm-overlay"
          onClick={() => setShowDeleteConfirm(false)}
        >
          <div
            className="session-confirm-dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>Delete Table?</h3>
            <p>
              This will permanently delete &ldquo;{table.name}&rdquo; and remove all
              members. This cannot be undone.
            </p>
            <div className="session-confirm-dialog__actions">
              <button
                className="btn btn--cancel"
                onClick={() => setShowDeleteConfirm(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn--end"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const charactersHeader = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 12,
};

const dmFormStyle = {
  border: '1px solid var(--border-light)',
  borderRadius: 6,
  padding: 16,
  marginBottom: 16,
  background: 'var(--bg-surface-alt)',
};

const dmFormHint = {
  marginTop: 8,
  fontSize: 12,
  color: 'var(--text-muted)',
};

const statusUnclaimed = {
  display: 'inline-block',
  fontSize: 11,
  color: 'var(--text-muted)',
  fontStyle: 'italic',
  marginBottom: 4,
};

const statusClaimed = {
  display: 'inline-block',
  fontSize: 11,
  color: 'var(--brand-primary)',
  marginBottom: 4,
};

const charActions = {
  display: 'flex',
  gap: 6,
  marginTop: 8,
  flexWrap: 'wrap',
};

const notesTextarea = {
  width: '100%',
  fontFamily: 'inherit',
  resize: 'vertical',
};

const notesActions = {
  display: 'flex',
  justifyContent: 'flex-end',
  marginTop: 10,
};

export default TableDetail;
