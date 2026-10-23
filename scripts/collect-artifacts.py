"""Publish final packages only, excluding source and temporary packaging folders."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,zipfile

parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True);parser.add_argument('--platform',required=True)
args=parser.parse_args();source=args.source.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
version=re.search(r'^version:\s*(\S+)',(source/'pubspec.yaml').read_text(encoding='utf-8'),re.M).group(1)
suffixes={'.zip','.exe','.apk','.dmg','.deb','.rpm','.AppImage'}
selected=[]
dist=source/'dist'
if dist.exists():
    for file in dist.rglob('*'):
        if not file.is_file() or file.is_symlink() or file.suffix not in suffixes:continue
        relative=file.relative_to(dist)
        if len(relative.parts)>2:continue
        if len(relative.parts)==2 and relative.parts[0]!=version:continue
        selected.append(file)
if args.platform=='ios':
    framework=source/'ios/Frameworks/libclash.xcframework'
    if framework.is_dir():
        archive=out/f'TutuCloud-{version}-ios-framework.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for file in framework.rglob('*'):
                if file.is_file() and not file.is_symlink():z.write(file,file.relative_to(framework.parent))
        selected.append(archive)
if not selected:raise RuntimeError('No final packages found; source directories will not be uploaded')
for file in selected:
    target=out/file.name
    if file.resolve()!=target.resolve():shutil.copy2(file,target)
if args.platform=='windows':
    if not list(out.glob('*.zip')) or not list(out.glob('*-setup.exe')):
        raise RuntimeError('Expected both Windows ZIP and setup installer')
head=subprocess.run(['git','rev-parse','HEAD'],cwd=source,capture_output=True,text=True,check=True).stdout.strip()
manifest={'version':version,'platform':args.platform,'source_commit':head,'packages':[]}
def digest(file):
    h=hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
for file in sorted(out.iterdir()):
    if file.is_file():manifest['packages'].append({'name':file.name,'bytes':file.stat().st_size,'sha256':digest(file)})
(out/'build-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Final packages collected; private source and temporary folders excluded.')
