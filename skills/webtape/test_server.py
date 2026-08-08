#!/usr/bin/env python3
"""Simple test server for WebTape demo."""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>WebTape Demo App</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            color: white;
        }
        .card {
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 3rem;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            max-width: 500px;
            width: 100%;
            color: #333;
        }
        h1 {
            font-size: 2rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p { line-height: 1.6; margin-bottom: 1.5rem; color: #666; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; font-weight: 600; margin-bottom: 0.5rem; }
        input {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }
        input:focus { outline: none; border-color: #667eea; }
        button {
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        .feature-list {
            margin: 2rem 0;
            padding: 0;
            list-style: none;
        }
        .feature-list li {
            padding: 0.75rem 0;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .feature-list li:last-child { border-bottom: none; }
        .check { color: #10b981; font-weight: bold; }
        .footer {
            margin-top: 2rem;
            text-align: center;
            font-size: 0.875rem;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎬 WebTape Demo</h1>
        <p>This is a sample web application used to demonstrate WebTape's browser recording capabilities.</p>
        
        <ul class="feature-list">
            <li><span class="check">✓</span> Declarative DSL like VHS</li>
            <li><span class="check">✓</span> Playwright-powered recording</li>
            <li><span class="check">✓</span> AI voice-over support</li>
            <li><span class="check">✓</span> Output to MP4/WebM/GIF</li>
        </ul>
        
        <div class="form-group">
            <label for="email">Email Address</label>
            <input type="email" id="email" placeholder="demo@webtape.dev">
        </div>
        
        <div class="form-group">
            <label for="message">Your Message</label>
            <input type="text" id="message" placeholder="Hello, WebTape!">
        </div>
        
        <button type="button" id="submit-btn">Get Started</button>
    </div>
    
    <div class="footer">
        WebTape POC - VHS-like browser recording
    </div>
    
    <script>
        document.getElementById('submit-btn').addEventListener('click', function() {
            alert('Thanks for trying WebTape! 🎬');
        });
    </script>
</body>
</html>
'''

class WebTapeHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        print(f"[test-server] {args[0]}")

def main():
    port = int(os.environ.get('PORT', 12000))
    server = HTTPServer(('0.0.0.0', port), WebTapeHandler)
    print(f"Test server running at http://localhost:{port}")
    server.serve_forever()

if __name__ == '__main__':
    main()
