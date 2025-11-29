block_cipher = None

a = Analysis([
             'entry_point.py'
             ],
             pathex=['.'],
             binaries=None,
             datas=[],
             hiddenimports=['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='DeltaSpread',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon='assets/icon.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='DeltaSpread')

app = BUNDLE(coll,
             name='DeltaSpread.app',
             icon='assets/icon.icns',
             bundle_identifier='com.github.namuan.deltaspread',
             info_plist={
                'CFBundleName': 'DeltaSpread',
                'CFBundleVersion': '0.1.0',
                'CFBundleShortVersionString': '0.1.0',
                'NSPrincipalClass': 'NSApplication',
                'NSHighResolutionCapable': 'True'
                }
             )
