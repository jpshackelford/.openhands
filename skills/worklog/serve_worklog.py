#!/usr/bin/env python3
"""
Simple HTTP server for worklog viewing
Serves /tmp/worklog.html on port 12000
"""
import http.server
import socketserver
import os

PORT = 12000
DIRECTORY = "/tmp"

class WorklogHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for worklog serving"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        """Add cache control headers"""
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        # Serve worklog.html for root path
        if self.path == '/':
            self.path = '/worklog.html'
        return super().do_GET()
    
    def log_message(self, format, *args):
        """Suppress request logging"""
        pass

def main():
    """Start the server"""
    os.chdir(DIRECTORY)
    
    with socketserver.TCPServer(("", PORT), WorklogHandler) as httpd:
        print(f"🌐 Worklog server running on port {PORT}")
        print(f"📍 Local: http://localhost:{PORT}/")
        print(f"🔗 Public: https://work-1-tahhvksgnhffxrqu.prod-runtime.all-hands.dev/")
        print(f"Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")

if __name__ == '__main__':
    main()
