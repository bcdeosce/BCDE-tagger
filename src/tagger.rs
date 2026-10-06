import subprocess, os
os.environ["PATH"] = f"/usr/local/cargo/bin:{os.environ.get('PATH','')}"

CLONE = "/content/_git_clone"
r = subprocess.run("cargo build --release", shell=True, cwd=CLONE,
                   capture_output=True, text=True, env=os.environ)
print(r.stdout[-2000:])
print(r.stderr[-2000:])

# Testa
BIN = f"{CLONE}/target/release/tagger"
DATA = f"{CLONE}/data"
for t in [
    "A sede da empresa é grande.",
    "Ele tem sede de justiça.",
    "Eu janto o jantar com molho.",
]:
    print(f"\n>>> {t}")
    r = subprocess.run([BIN, DATA], input=t+"\n",
                       capture_output=True, text=True)
    print(r.stdout.rstrip())
