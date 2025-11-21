Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "wsl bash -c ""cd /root/gemini_gradio_app && ./venv/bin/python3 app.py""", 0, False
WScript.Sleep 5000
WshShell.Run "http://127.0.0.1:7860/", 1, False
Set WshShell = Nothing