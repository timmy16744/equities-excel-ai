#!/usr/bin/env python3
"""
Simple HTTP server for Equities AI Excel Interface
Run with: python server.py
Then open http://localhost:3000 in your browser
"""

import http.server
import socketserver
import os
import webbrowser
from functools import partial

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"""
╔═══════════════════════════════════════════════════════════════╗
║           EQUITIES AI - EXCEL INTERFACE                       ║
╠═══════════════════════════════════════════════════════════════╣
║  Server running at: http://localhost:{PORT}                     ║
║                                                               ║
║  Features:                                                    ║
║  - Dashboard: Agent consensus & market overview               ║
║  - Agents: Detailed view of all 12 AI agents                  ║
║  - Portfolio: Position tracking & P&L                         ║
║  - Performance: Agent accuracy & calibration                  ║
║  - Signals: Trade signals & recommendations                   ║
║  - Risk: Risk metrics & alerts                                ║
║  - Settings: Configuration management                         ║
║                                                               ║
║  Keyboard Shortcuts:                                          ║
║  - Ctrl+R: Refresh data                                       ║
║  - Ctrl+E: Export report                                      ║
║  - 1-9: Switch views                                          ║
║  - Esc: Close modal                                           ║
║                                                               ║
║  Note: Running in demo mode (no backend required)             ║
║  Connect to backend at http://localhost:8000 for live data    ║
║                                                               ║
║  Press Ctrl+C to stop the server                              ║
╚═══════════════════════════════════════════════════════════════╝
""")

        # Try to open browser
        try:
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
