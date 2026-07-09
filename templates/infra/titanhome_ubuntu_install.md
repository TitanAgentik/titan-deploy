# TITANHOME Ubuntu 24.04 Install Guide

Target: Micron 7500 Pro 3.8TB | Hostname: `titanhome` | IP: `192.168.10.10`

## 1. Create boot USB (on any PC)

```bash
# Download Ubuntu 24.04.4 LTS Desktop or Server ISO
# https://ubuntu.com/download/desktop

# Write with balenaEtcher or:
sudo dd if=ubuntu-24.04.4-desktop-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

Use **Desktop** if you want a GUI for initial setup; **Server** for headless + AST2600 BMC.

## 2. Boot installer

1. Insert USB into TITANHOME rear port.
2. Power on → press **F8** for boot menu (or Del → Boot → USB). Local KVM or AST2600 BMC if remote.
3. Select Ubuntu USB.

## 3. Installer choices

| Screen | Choice |
|--------|--------|
| Language | English |
| Keyboard | Your layout |
| Connect to network | **Skip WiFi** — use Ethernet if switch ready; offline OK for install |
| Updates | Normal installation + **Download updates** if online |
| Install type | **Something else** (manual partitions) — see below |
| Hostname | `titanhome` |
| Username | `hyperion` |
| Password | Strong password + **no** auto-login for production |

### Partitioning — Simple (recommended first install)

Target disk: **Micron 7500** (~3.8TB) — confirm by model in installer!

| Partition | Size | Type | Mount |
|-----------|------|------|-------|
| EFI | 512 MB | EFI System Partition | `/boot/efi` |
| root | 200 GB | ext4 | `/` |
| swap | 64 GB | swap | (swap) |
| data | remainder | ext4 | `/data` |

Leave WD SN8100 drives **unformatted** until post-install (then add ZFS or mount as `/fast`).

### Partitioning — ZFS (advanced, matches Titan spec)

Choose **Use ZFS** only if installer offers it on 24.04 Desktop custom install, or use manual:

- Install minimal ext4 `/` first, add ZFS pools post-install (see postinstall script).

## 4. Complete install

- Remove USB when prompted.
- Reboot → enter BIOS → set **Boot Option #1** to Micron NVMe.
- Boot into Ubuntu.

## 5. First login checks

```bash
uname -m          # x86_64
lscpu | head -20
free -h           # ~512Gi
lsblk
ip link           # note Ethernet interface name for netplan
```

## 6. Static IP (after Ethernet connected to switch)

```bash
sudo nano /etc/netplan/01-titanhome.yaml
```

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1:                    # REPLACE with your interface from `ip link`
      addresses:
        - 192.168.10.10/24
      routes:
        - to: default
          via: 192.168.10.1
      nameservers:
        addresses:
          - 192.168.10.1
          - 1.1.1.1
```

```bash
sudo chmod 600 /etc/netplan/01-titanhome.yaml
sudo netplan apply
hostnamectl set-hostname titanhome
```

## 7. NVIDIA drivers (required before Titan)

```bash
sudo apt update && sudo apt upgrade -y
sudo ubuntu-drivers list
sudo ubuntu-drivers install   # or: sudo apt install nvidia-driver-580
sudo reboot
```

After reboot:

```bash
nvidia-smi -L    # MUST show 2× RTX PRO 6000
nvidia-smi       # both GPUs, no errors
```

## 8. Run Titan post-install script

Copy from titan-deploy:

```bash
bash /path/to/titan-deploy/scripts/titanhome-postinstall.sh
```

## 9. Deploy Titan bundle

```bash
cd ~/Documents/Cursor\ Projects/titan-deploy
./deploy.sh
./verify.sh
```