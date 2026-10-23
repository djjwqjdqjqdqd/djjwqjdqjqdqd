from pathlib import Path
import json,subprocess,tempfile,unittest

class FinalPackageTests(unittest.TestCase):
    def test_only_final_packages_leave_private_source_tree(self):
        collector=Path(__file__).with_name('collect-artifacts.py').resolve()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();out=root/'out'
            subprocess.run(['git','init',str(source)],capture_output=True,check=True)
            (source/'pubspec.yaml').write_text('version: 0.3.12+42\n')
            subprocess.run(['git','add','pubspec.yaml'],cwd=source,capture_output=True,check=True)
            subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture'],cwd=source,capture_output=True,check=True)
            dist=source/'dist/0.3.12+42';dist.mkdir(parents=True)
            (dist/'fl_clash-windows.zip').write_bytes(b'final ZIP fixture')
            (dist/'fl_clash-windows-setup.exe').write_bytes(b'installer fixture')
            staging=dist/'temporary-setup';staging.mkdir()
            (staging/'private-source.dart').write_text('private source fixture')
            (staging/'keystore.jks').write_bytes(b'signing fixture')
            (staging/'application.exe').write_bytes(b'temporary executable')
            subprocess.run(['python',str(collector),'--source',str(source),'--out',str(out),'--platform','windows'],capture_output=True,check=True)
            self.assertEqual({p.name for p in out.iterdir()},{'fl_clash-windows.zip','fl_clash-windows-setup.exe','build-manifest.json'})
            manifest=json.loads((out/'build-manifest.json').read_text())
            self.assertEqual(manifest['version'],'0.3.12+42')
            self.assertEqual(len(manifest['packages']),2)

if __name__=='__main__':unittest.main()
