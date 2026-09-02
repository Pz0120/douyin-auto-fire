"""Debug script to check SMTP environment variables in GitHub Actions."""
import os
import json

# Check raw env vars
smtp_server = os.environ.get("SMTP_SERVER", "<NOT SET>")
smtp_port = os.environ.get("SMTP_PORT", "<NOT SET>")
smtp_user = os.environ.get("SMTP_USER", "<NOT SET>")
smtp_pass = os.environ.get("SMTP_PASS", "<NOT SET>")
smtp_to = os.environ.get("SMTP_TO", "<NOT SET>")

# Write to a file for inspection
with open("debug_env_result.txt", "w", encoding="utf-8") as f:
    f.write(f"SMTP_SERVER={smtp_server!r}\n")
    f.write(f"SMTP_PORT={smtp_port!r}\n")
    f.write(f"SMTP_USER={smtp_user!r}\n")
    f.write(f"SMTP_PASS={smtp_pass!r}\n")
    f.write(f"SMTP_TO={smtp_to!r}\n")
    f.write(f"\n")
    f.write(f"SMTP_PORT type: {type(smtp_port).__name__}\n")
    f.write(f"SMTP_PORT length: {len(smtp_port)}\n")
    f.write(f"SMTP_PORT isdigit(): {smtp_port.isdigit() if isinstance(smtp_port, str) else 'N/A'}\n")
    try:
        f.write(f"SMTP_PORT int(): {int(smtp_port)}\n")
    except Exception as e:
        f.write(f"SMTP_PORT int() FAILED: {e}\n")

# Also print for logs
print(f"SMTP_SERVER={smtp_server}")
print(f"SMTP_PORT={smtp_port}")
print(f"SMTP_USER={smtp_user}")
print(f"SMTP_PASS set: {'yes' ifsmtp_pass != '<NOT SET>' else 'no'}")
print(f"SMTP_TO={smtp_to}")

# Check if there's a .env file
if os.path.exists(".env"):
    print("\n.env file exists:")
    with open(".env", "r") as env_f:
        print(env_f.read())
else:
    print("\nNo .env file found")

# List all files in current directory
print("\nFiles in current directory:")
for f in os.listdir("."):
    print(f"  {f}")
