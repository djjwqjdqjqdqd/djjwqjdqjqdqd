from pathlib import Path
import base64,os,subprocess,tempfile,unittest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class PrivateBuildLogTests(unittest.TestCase):
    def test_secret_output_is_encrypted_and_exit_code_is_preserved(self):
        wrapper=Path(__file__).with_name('private-run.mjs').resolve()
        for code in [0,7]:
            with self.subTest(code=code),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);script=root/'input.txt';secret='private-source-and-secret-fixture'
                windows=os.name=='nt'
                script.write_text((f'Write-Output "{secret}"\nexit {code}' if windows else f'echo "{secret}"\nexit {code}'),encoding='utf-8')
                key=os.urandom(32);env=os.environ.copy();env.update(BUILD_LOG_KEY=base64.b64encode(key).decode(),RUNNER_TEMP=temp)
                p=subprocess.run(['node',str(wrapper),str(script)],env=env,capture_output=True,text=True)
                self.assertEqual(p.returncode,code)
                self.assertNotIn(secret,p.stdout+p.stderr)
                data=next((root/'build-logs').glob('*.enc')).read_bytes()
                self.assertNotIn(secret.encode(),data)
                decrypt=wrapper.with_name('decrypt-log.mjs');output=root/'clear.log'
                check=subprocess.run(['node',str(decrypt),str(next((root/'build-logs').glob('*.enc'))),str(output)],env=env,capture_output=True,text=True)
                self.assertEqual(check.returncode,0,check.stderr)
                self.assertIn(secret,output.read_text())

    def test_interrupted_records_require_opt_in_and_detect_tampering(self):
        decrypt=Path(__file__).with_name('decrypt-log.mjs').resolve()
        key=os.urandom(32);secret=b'authenticated-progress-fixture'
        nonce=os.urandom(12);cipher=AESGCM(key).encrypt(nonce,secret,(0).to_bytes(8,'big'))
        record=nonce+cipher
        data=b'BLDLOG02'+len(record).to_bytes(4,'big')+record
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'log.enc';out=root/'clear.log'
            env=os.environ.copy();env['BUILD_LOG_KEY']=base64.b64encode(key).decode()
            source.write_bytes(data+b'\x00\x00')
            def run(*args):return subprocess.run(['node',str(decrypt),str(source),str(out),*args],env=env,capture_output=True,text=True)
            self.assertNotEqual(run().returncode,0)
            self.assertFalse(out.exists())
            self.assertEqual(run('--allow-incomplete').returncode,0)
            self.assertEqual(out.read_bytes(),secret)
            out.unlink()
            damaged=bytearray(data);damaged[-1]^=1;source.write_bytes(damaged)
            self.assertNotEqual(run('--allow-incomplete').returncode,0)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
