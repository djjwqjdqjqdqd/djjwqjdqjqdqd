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
                data=next((root/'tutu-build-logs').glob('*.enc')).read_bytes()
                self.assertNotIn(secret.encode(),data)
                clear=AESGCM(key).decrypt(data[8:20],data[20:],None)
                self.assertIn(secret.encode(),clear)

if __name__=='__main__':unittest.main()
