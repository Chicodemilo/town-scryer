# ==============================================================================
# File:      api/app/routes/logs.py
# Purpose:   Logging route blueprint. Receives frontend error and info
#            messages via POST and writes them to server-side log files.
#            Includes a health check for the logging subsystem.
# Callers:   routes/__init__.py
# Callees:   Flask, os, datetime, threading
# Modified:  2026-04-22
# ==============================================================================
"""
Logging Routes - Handle frontend error logging to files

This module provides endpoints for frontend applications to log errors
and other messages to server-side log files.
"""

from flask import Blueprint, request, jsonify
import os
from datetime import datetime
import threading

# Create Blueprint
logs_bp = Blueprint('logs', __name__)

# Thread lock for file writing
file_lock = threading.Lock()

def ensure_logs_directory():
    """Ensure the logs directory exists"""
    logs_dir = '/app/logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def write_to_log_file(filename, message):
    """Thread-safe write to log file"""
    logs_dir = ensure_logs_directory()
    file_path = os.path.join(logs_dir, filename)
    
    with file_lock:
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
                f.flush()  # Ensure immediate write
            return True
        except Exception as e:
            print(f"Error writing to log file {filename}: {e}")
            return False

@logs_bp.route('/error', methods=['POST'])
def log_error():
    """
    Log frontend errors to error_log.txt
    
    Expected JSON payload:
    {
        "message": "Formatted error message",
        "timestamp": "ISO timestamp"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        message = data['message']
        
        # Write to error log file
        success = write_to_log_file('error_log.txt', message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Error logged successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to write to log file'
            }), 500
            
    except Exception as e:
        print(f"Error in log_error endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@logs_bp.route('/info', methods=['POST'])
def log_info():
    """
    Log frontend info messages to info_log.txt
    
    Expected JSON payload:
    {
        "message": "Formatted info message",
        "timestamp": "ISO timestamp"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        message = data['message']
        
        # Write to info log file
        success = write_to_log_file('info_log.txt', message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Info logged successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to write to log file'
            }), 500
            
    except Exception as e:
        print(f"Error in log_info endpoint: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@logs_bp.route('/health', methods=['GET'])
def logs_health():
    """Health check for logging system"""
    try:
        logs_dir = ensure_logs_directory()
        
        return jsonify({
            'success': True,
            'message': 'Logging system healthy',
            'logs_directory': logs_dir,
            'writable': os.access(logs_dir, os.W_OK)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
