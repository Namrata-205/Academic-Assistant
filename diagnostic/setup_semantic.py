"""Download a pinned local multilingual embedding model; never uploads learner text."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent.parent
REPOSITORY='Xenova/paraphrase-multilingual-MiniLM-L12-v2'

def setup():
    folder=ROOT/'assets'/'models'/'multilingual-minilm'
    folder.mkdir(parents=True,exist_ok=True)
    with urlopen('https://huggingface.co/api/models/'+REPOSITORY,timeout=60) as response:
        revision=json.load(response)['sha']
    files=[]
    for filename in ('tokenizer.json','config.json','onnx/model_quantized.onnx'):
        output=folder/Path(filename).name
        url=f'https://huggingface.co/{REPOSITORY}/resolve/{revision}/{filename}'
        if not output.exists():
            temporary=output.with_suffix(output.suffix+'.part')
            with urlopen(url,timeout=60) as response,temporary.open('wb') as stream:
                while block:=response.read(1024*1024):stream.write(block)
            temporary.replace(output)
        files.append({'filename':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
        print(f'Ready: {output.name}',flush=True)
    manifest={'repository':REPOSITORY,'revision':revision,'files':files,
              'license':'Apache-2.0 (upstream model)','usage':'Local CPU embeddings; no remote code or question upload.'}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Local semantic model ready',flush=True)

if __name__=='__main__':setup()
