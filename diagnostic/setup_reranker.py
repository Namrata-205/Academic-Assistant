"""Explicit download of a pinned public ONNX reranker; no learner data uploads."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
REVISION='1427fd652930e4ba29e8149678df786c240d8825'
FOLDER=ROOT/'assets/models/multilingual-reranker'


def setup():
    FOLDER.mkdir(parents=True,exist_ok=True)
    revision=REVISION;files=[];expected={}
    existing=FOLDER/'manifest.json'
    if existing.exists():
        saved=json.loads(existing.read_text())
        if saved['repository']!=REPOSITORY or saved['revision']!=revision:
            raise ValueError('Existing model has a different revision; preserve it separately before updating.')
        expected={entry['filename']:entry['sha256'] for entry in saved['files']}
    for filename in ('config.json','tokenizer.json','onnx/model_quint8_avx2.onnx'):
        target=FOLDER/Path(filename).name;temporary=target.with_suffix(target.suffix+'.part')
        if target.exists() and target.name in expected and hashlib.sha256(target.read_bytes()).hexdigest()!=expected[target.name]:
            raise ValueError('Existing artifact hash mismatch: '+target.name)
        if not target.exists():
            url=f'https://huggingface.co/{REPOSITORY}/resolve/{revision}/{filename}'
            with urlopen(url,timeout=60) as response,temporary.open('wb') as stream:
                while block:=response.read(1024*1024):stream.write(block)
            temporary.replace(target)
        files.append({'filename':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                      'bytes':target.stat().st_size})
        print('Ready:',target.name,target.stat().st_size,'bytes',flush=True)
    manifest={'repository':REPOSITORY,'revision':revision,'files':files,
              'upstream':'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',
              'license':'Apache-2.0 (upstream model)',
              'usage':'Local query-passage reranking on CPU. No remote code or learner text uploads.'}
    existing.write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print('Reranker ready at',FOLDER,flush=True)


if __name__=='__main__':setup()
