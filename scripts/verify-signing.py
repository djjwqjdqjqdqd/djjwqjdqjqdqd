"""Verify an APK against the preserved release keystore without publishing keys."""
from pathlib import Path
import argparse,base64,hashlib,json,os,re,subprocess,tempfile

parser=argparse.ArgumentParser();parser.add_argument('--artifacts',type=Path,required=True)
args=parser.parse_args();apks=list(args.artifacts.rglob('*.apk'))
if not apks:raise RuntimeError('No APK found in the selected artifact')
sdk=Path(os.environ.get('ANDROID_HOME',os.environ.get('ANDROID_SDK_ROOT','/usr/local/lib/android/sdk')))
tools=sorted((sdk/'build-tools').glob('*/apksigner'),key=lambda p:tuple(int(v) if v.isdigit() else 0 for v in p.parent.name.split('.')))
if not tools:raise RuntimeError('Android signature verifier is unavailable')
keytool=Path(os.environ['JAVA_HOME'])/'bin/keytool'
with tempfile.TemporaryDirectory(prefix='signing-check-') as temp:
    root=Path(temp);keystore=root/'signing.jks';certificate=root/'certificate.der'
    keystore.write_bytes(base64.b64decode(''.join(os.environ['ANDROID_KEYSTORE_BASE64'].split()),validate=True));keystore.chmod(0o600)
    p=subprocess.run([str(keytool),'-exportcert','-keystore',str(keystore),'-alias',os.environ['ANDROID_KEY_ALIAS'],'-storepass:env','ANDROID_STORE_PASSWORD','-file',str(certificate)],capture_output=True)
    if p.returncode:raise RuntimeError('Could not read the preserved signing certificate')
    expected=hashlib.sha256(certificate.read_bytes()).hexdigest();packages=[]
    for apk in apks:
        p=subprocess.run([str(tools[-1]),'verify','--verbose','--print-certs',str(apk)],capture_output=True,text=True)
        if p.returncode:raise RuntimeError('APK signature verification failed')
        fingerprints=re.findall(r'Signer #\d+ certificate SHA-256 digest:\s*([0-9a-fA-F]{64})',p.stdout)
        if {v.lower() for v in fingerprints}!={expected}:raise RuntimeError('APK signing identity differs from the preserved release keystore')
        packages.append({'name':apk.name,'signature_valid':True,'preserved_keystore_matches':True})
report={'packages':packages,'signing_identity_preserved':True}
Path('signing-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('APK signature is valid and matches the preserved release keystore.')
