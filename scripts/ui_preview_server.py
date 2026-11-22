"""Local UI verification server using a separate database and offline generation."""
import argparse
from pathlib import Path
import sys
import os
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostic import engine,chat_provider
from server import Handler,LocalHTTPServer

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--database',type=Path,default=ROOT/'.dist/ui-preview.sqlite3')
    args=parser.parse_args();connect=engine.connect
    with patch.object(engine,'connect',side_effect=lambda:connect(args.database)),patch('diagnostic.chat_router.gemini_generate',side_effect=chat_provider.ProviderError('offline_ui_test')),patch('diagnostic.book_chat.gemini_generate',side_effect=chat_provider.ProviderError('offline_ui_test')),patch('diagnostic.practice.gemini_generate',side_effect=chat_provider.ProviderError('offline_ui_test')):
        server=LocalHTTPServer(('127.0.0.1',args.port),Handler)
        print(f'Isolated UI preview: http://127.0.0.1:{server.server_port} (PID {os.getpid()})',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
