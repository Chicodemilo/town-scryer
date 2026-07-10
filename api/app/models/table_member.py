# ==============================================================================
# File:      api/app/models/table_member.py
# Purpose:   TableMember model. Join table linking users to game tables with
#            role (owner/player) and join timestamp.
# Callers:   models/__init__.py
# Callees:   SQLAlchemy (db), datetime
# Modified:  2026-06-01
# ==============================================================================
from app import db
from datetime import datetime


class TableMember(db.Model):
    __tablename__ = 'table_member'

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('game_table.id'),
                         nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'owner' or 'player'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint: one membership per user per table
    __table_args__ = (
        db.UniqueConstraint('table_id', 'user_id', name='uq_table_user'),
    )

    # Relationships
    user = db.relationship('User', backref=db.backref('table_memberships',
                                                      lazy='dynamic'))

    def __repr__(self):
        return f'<TableMember table={self.table_id} user={self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'table_id': self.table_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
        }
