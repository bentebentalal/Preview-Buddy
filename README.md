# Preview Buddy for Blender 🎬

A smart viewport preview addon that remembers your per‑camera settings and makes quick renders a breeze.

---

##  Key Features

- 📸 **Per‑Camera Frame Range Memory**  
  Each camera remembers its own frame range settings.  
- 🔄 **Queue/Batch Processing**  
  Render multiple camera setups in sequence.  
- 💾 **Settings Backup/Restore**  
  Never lose your render settings after a preview.  
- 🎯 **Multiple Output Formats**  
  MP4, MOV, PNG sequence, JPEG sequence.  
- 📈 **Incremental Saving**  
  Automatically version your previews (v001, v002, etc.).  
- ⚡ **Quick Viewport Renders**  
  OpenGL viewport rendering for fast previews.  
- 🎯 **Direct Output**  
  Renders directly to file instead of screen-first approach.
---

## 🚀 Installation

1. Download the latest `PreviewBuddy.py` file.  
2. In Blender, go to **Edit → Preferences → Add‑ons**.  
3. Click **Install**, select `PreviewBuddy.py`, and click **Install Add‑on**.  
4. Enable **Preview Buddy** in the add‑on list.  
5. Find **Preview Buddy** in the 3D Viewport sidebar (press `N`).

---

## 🎯 Quick Start

1. Open the **Preview Buddy** panel in the 3D Viewport sidebar.  
2. Select a camera or use **Active Viewport**.  
3. Set your frame range (Timeline or Custom).  
4. Click **MAKE PREVIEW**.  
5. Your preview will be saved to the output folder.

---

## 📖 Usage Guide

### Camera Settings 📷

- Select cameras from the dropdown.  
- Each camera automatically remembers its frame range.  
- Use **Timeline** or **Custom** frame ranges.  
- Delete stored ranges with the **X** button.

### Output Settings 💾

- Choose from **MP4**, **MOV**, **PNG**, or **JPEG** formats.  
- **Incremental Save** creates versioned files (v001, v002…).  
- **Overwrite Mode** replaces existing files.  
- **Auto‑Open Preview** opens the file after render.  
- Custom output paths supported.

### Queue System 🔄

- Add multiple cameras to the render queue.  
- Set different frame ranges for each camera.  
- Process all queued renders in one click.  
- Enable/disable individual queue items.

### Performance Options ⚡

- Override FPS for previews.  
- Custom resolution scaling.  
- Enable/disable **Simplify**.  
- Metadata burn‑in with adjustable font size.

---

## ⚙️ Advanced Features

### Per‑Camera Frame Range Memory 🧠

Each camera remembers its own frame range so you don’t have to manually adjust ranges when switching cameras.

### Smart File Naming 📝

- Optional scene name inclusion.  
- Camera name in filename.  
- Frame range in filename.  
- Automatic versioning.

### Settings Protection 🛡️

Preview Buddy backs up your render settings before preview and restores them afterward.

---

## 🆓 Free & Open Source

Preview Buddy is completely free! If you find it helpful,
consider a donation at https://ko-fi.com/bentebent

---

## 🐛 Troubleshooting

- Enable **Debug Mode** in addon preferences to see detailed logs.  
- Check the Blender console for error messages.  
- Use **Restore Settings** if something goes wrong.  
- Requires a saved `.blend` file to work properly.

---

## 📝 License

This project is licensed under the **GPL‑3.0 License**.  
See the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Feel free to submit issues and pull requests! I’m always happy to improve Preview Buddy.

---

## 📞 Support

- Report issues on [GitHub](https://github.com/bentebentalal/Preview-Buddy/issues).  

---

Made with ❤️ for the Blender community.  
