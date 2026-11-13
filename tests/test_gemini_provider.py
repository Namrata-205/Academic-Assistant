import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch
from diagnostic import book_chat as chat
from diagnostic import chat_provider as provider


class Reply:
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,*args):return json.dumps(self.payload).encode()


class GeminiProviderTests(unittest.TestCase):
    def test_env_file_quotes_allowlist_and_process_precedence(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{},clear=True):
            path=Path(tmp)/'.env';path.write_text('GEMINI_API_KEY="file-secret"\nIGNORED=unused\nATLAS_CHAT_MODEL=gemini-3.5-flash-lite\n',encoding='utf-8')
            config=provider.configuration(path);self.assertEqual(config['GEMINI_API_KEY'],'file-secret')
            self.assertNotIn('IGNORED',config)
            with patch.dict(os.environ,{'GEMINI_API_KEY':'env-secret'}):
                self.assertEqual(provider.configuration(path)['GEMINI_API_KEY'],'env-secret')

    def test_gemini_payload_and_source_validation_exclude_learner_records(self):
        source={'id':'S1','excerpt':'An angle has two arms sharing a common endpoint called the vertex.','concept_id':'MATH6_C0020'}
        draft={'paragraphs':[{'text':'An angle has two arms.','citations':['S1'],'evidence':source['excerpt']}]}
        raw={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(draft)}]}}]}
        config={'ATLAS_CHAT_PROVIDER':'gemini','GEMINI_API_KEY':'test-secret'}
        with patch.object(chat,'configuration',return_value=config),patch.object(provider,'urlopen',return_value=Reply(raw)) as call:
            output=chat.generate('Briefly explain an angle.','angle','en',[source],[],{'private_history':'NEVER_SEND_THIS','imported_background':'PRIVATE'})
            status=chat.model_status()
        request=call.call_args.args[0];body=json.loads(request.data)
        self.assertEqual(output[0]['citations'],['S1'])
        self.assertIn('gemini-3.5-flash-lite:generateContent',request.full_url)
        self.assertNotIn('test-secret',request.full_url)
        self.assertEqual(request.get_header('X-goog-api-key'),'test-secret')
        self.assertEqual(body['generationConfig']['responseMimeType'],'application/json')
        self.assertNotIn('NEVER_SEND_THIS',request.data.decode());self.assertNotIn('PRIVATE',request.data.decode())
        self.assertNotIn('test-secret',json.dumps(status));self.assertFalse(status['local_only'])

    def test_missing_key_status_and_errors_are_sanitized(self):
        with patch.object(chat,'configuration',return_value={'ATLAS_CHAT_PROVIDER':'gemini'}),patch.object(provider,'urlopen') as call:
            self.assertFalse(chat.model_status()['generation_available'])
            with self.assertRaises(provider.ProviderError):provider.gemini_generate('system','prompt','gemini-3.5-flash-lite','')
            call.assert_not_called()
        with patch.object(provider,'urlopen',side_effect=HTTPError('https://example.test',429,'secret-should-not-leak',{},None)):
            with self.assertRaisesRegex(provider.ProviderError,'^quota_or_rate_limit$'):
                provider.gemini_generate('system','prompt','gemini-3.5-flash-lite','test-secret')

    def test_blocked_response_and_fake_source_fail_closed(self):
        with patch.object(provider,'urlopen',return_value=Reply({'candidates':[]})):
            with self.assertRaisesRegex(provider.ProviderError,'blocked_or_incomplete'):
                provider.gemini_generate('system','prompt','gemini-3.5-flash-lite','test-secret')
        with patch.object(chat,'configuration',return_value={'ATLAS_CHAT_PROVIDER':'gemini','GEMINI_API_KEY':'test-secret'}),patch.object(chat,'gemini_generate',return_value={'paragraphs':[{'text':'wrong','citations':['S99'],'evidence':'a made-up supporting evidence quote'}]}):
            with self.assertRaises(ValueError):chat.generate('angle','angle','en',[],[])


if __name__=='__main__':unittest.main()
