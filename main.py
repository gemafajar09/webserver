import subprocess
import sys
import os

def install_if_missing(module_name, pip_name=None):
    try:
        __import__(module_name)
    except ImportError:
        package = pip_name if pip_name else module_name
        print(f"Menginstall package '{package}'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_if_missing("flask")
install_if_missing("speedtest", "speedtest-cli")

import shutil
from flask import Flask, render_template, request, redirect, url_for, flash
import speedtest
import zipfile
import urllib.request
import logging

app = Flask(__name__)
app.secret_key = "secret-key-1234"

# Setup logging
logging.basicConfig(level=logging.INFO)

# ============================
# Konfigurasi dan Konstanta
# ============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PHP_DOWNLOAD_LINKS = {
    "7.2": "https://windows.php.net/downloads/releases/archives/php-7.2.9-nts-Win32-VC15-x64.zip",
    "7.3": "https://windows.php.net/downloads/releases/archives/php-7.3.9-nts-Win32-VC15-x64.zip",
    "7.4": "https://windows.php.net/downloads/releases/archives/php-7.4.9-Win32-vc15-x64.zip",
    "8.0": "https://windows.php.net/downloads/releases/archives/php-8.0.9-Win32-vs16-x64.zip",
    "8.1": "https://windows.php.net/downloads/releases/archives/php-8.1.30-nts-Win32-vs16-x64.zip",
    "8.2": "https://windows.php.net/downloads/releases/archives/php-8.2.27-nts-Win32-vs16-x64.zip",
    "8.3": "https://windows.php.net/downloads/releases/archives/php-8.3.18-nts-Win32-vs16-x64.zip",
    "8.4": "https://windows.php.net/downloads/releases/archives/php-8.4.5-nts-Win32-vs17-x64.zip",
}

APACHE_DOWNLOAD_LINKS = {
    "2.4": "https://www.apachelounge.com/download/VS16/binaries/httpd-2.4.57-win64-VS16.zip"
}

MYSQL_DOWNLOAD_LINKS = {
    "5.7": "https://dev.mysql.com/get/Downloads/MySQL-5.7/mysql-5.7.39-winx64.zip",
    "8.0": "https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.40-winx64.zip",
    "8.4": "https://dev.mysql.com/get/Downloads/MySQL-8.4/mysql-8.4.3-winx64.zip",
    "9.1": "https://dev.mysql.com/get/Downloads/MySQL-9.1/mysql-9.1.0-winx64.zip",
}

PHP_DIR = os.path.join(BASE_DIR, "php")
APACHE_DIR = os.path.join(BASE_DIR, "apache")
MYSQL_DIR = os.path.join(BASE_DIR, "mysql")
TMP_DIR = os.path.join(BASE_DIR, "tmp")
WWW_DIR = os.path.join(BASE_DIR, "www")

# Status dan Versi Aktif
service_status = {
    "apache": False,
    "mysql": False,
}

active_versions = {
    "php": None,
    "apache": None,
}

network_speed_result = {}

# ============================
# Fungsi Helper Service
# ============================
def run_process(executable, args=None):
    try:
        args = args or []
        proc = subprocess.Popen([executable] + args, creationflags=subprocess.CREATE_NO_WINDOW)
        logging.info(f"Started process {executable} with PID {proc.pid}")
        return True, None
    except Exception as e:
        logging.error(f"Failed to start process {executable}: {e}")
        return False, str(e)

def kill_process(process_name):
    try:
        subprocess.run(["taskkill", "/F", "/IM", process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"Killed process {process_name}")
        return True, None
    except Exception as e:
        logging.error(f"Failed to kill process {process_name}: {e}")
        return False, str(e)

# Apache
def start_apache(version):
    apache_versions = get_installed_apache_versions()
    path = apache_versions.get(version)
    if not path:
        return False, f"Versi Apache {version} tidak ditemukan!"
    
    apache_exe = os.path.join(path, "bin", "httpd.exe")
    if not os.path.isfile(apache_exe):
        return False, f"Apache executable tidak ditemukan di {apache_exe}!"
    
    success, err = run_process(apache_exe)
    if success:
        service_status["apache"] = True
        active_versions["apache"] = version
        return True, f"Apache {version} started"
    else:
        return False, err

def stop_apache():
    success, err = kill_process("httpd.exe")
    if success:
        service_status["apache"] = False
        active_versions["apache"] = None
        return True, "Apache stopped"
    else:
        return False, err

def download_and_extract_apache(version):
    if version not in APACHE_DOWNLOAD_LINKS:
        return False, f"Link untuk Apache {version} tidak tersedia."

    url = APACHE_DOWNLOAD_LINKS[version]

    target_dir = os.path.join(APACHE_DIR, f"apache-{version}")
    zip_path = os.path.join(BASE_DIR, f"apache-{version}.zip")

    if os.path.isdir(target_dir):
        return False, f"Apache versi {version} sudah terinstal."

    os.makedirs(APACHE_DIR, exist_ok=True)

    try:
        success, err = download_with_progress(url, zip_path)
        if not success:
            return False, f"Gagal download atau ekstrak Apache: {err}"
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        os.remove(zip_path)
        return True, f"Apache {version} berhasil diunduh dan diekstrak."
    except Exception as e:
        return False, f"Gagal download atau ekstrak Apache: {e}"

def get_installed_apache_versions():
    if not os.path.isdir(APACHE_DIR):
        return {}
    versions = {}
    for folder_name in os.listdir(APACHE_DIR):
        full_path = os.path.join(APACHE_DIR, folder_name)
        if os.path.isdir(full_path) and folder_name.startswith("apache-"):
            version = folder_name.replace("apache-", "")
            versions[version] = full_path
    return versions

# MySQL
def start_mysql(version=None):
    mysql_versions = get_installed_mysql_versions()
    if not version:
        version = active_versions.get("mysql")
    if not version or version not in mysql_versions:
        return False, "Versi MySQL tidak ditemukan atau belum aktif."

    mysql_exe = os.path.join(mysql_versions[version], "bin", "mysqld.exe")
    if not os.path.isfile(mysql_exe):
        return False, f"MySQL executable tidak ditemukan di {mysql_exe}!"

    success, err = run_process(mysql_exe)
    if success:
        service_status["mysql"] = True
        active_versions["mysql"] = version
        return True, f"MySQL {version} started"
    else:
        return False, err

def stop_mysql():
    success, err = kill_process("mysqld.exe")
    if success:
        service_status["mysql"] = False
        active_versions["mysql"] = None
        return True, "MySQL stopped"
    else:
        return False, err

def download_and_extract_mysql(version):
    if version not in MYSQL_DOWNLOAD_LINKS:
        return False, f"Link untuk MySQL {version} tidak tersedia."

    url = MYSQL_DOWNLOAD_LINKS[version]
    zip_path = os.path.join(BASE_DIR, f"mysql-{version}.zip")
    temp_extract_dir = os.path.join(MYSQL_DIR, f"_tmp_mysql_{version}")
    final_dir = os.path.join(MYSQL_DIR, f"mysql-{version}")

    if os.path.isdir(final_dir):
        return False, f"MySQL versi {version} sudah terinstal."

    os.makedirs(MYSQL_DIR, exist_ok=True)

    try:
        success, err = download_with_progress(url, zip_path)
        if not success:
            return False, f"Gagal download file: {err}"

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)

        os.remove(zip_path)

        extracted = os.listdir(temp_extract_dir)
        if len(extracted) == 1 and os.path.isdir(os.path.join(temp_extract_dir, extracted[0])):
            shutil.move(os.path.join(temp_extract_dir, extracted[0]), final_dir)
            shutil.rmtree(temp_extract_dir)
        else:
            shutil.move(temp_extract_dir, final_dir)

        ini_success, ini_msg = create_mysql_ini(version)
        if not ini_success:
            return False, f"MySQL berhasil diunduh tapi gagal membuat my.ini: {ini_msg}"

        init_success, init_msg = initialize_mysql_data(version)
        if not init_success:
            return False, f"MySQL berhasil diunduh, tapi gagal inisialisasi data: {init_msg}"

        import time
        time.sleep(2)
        pass_success, pass_msg = change_mysql_root_password(version, new_password="mysql")
        if not pass_success:
            return False, f"MySQL diinisialisasi, tapi gagal ubah password root: {pass_msg}"

        return True, f"MySQL {version} berhasil diinstal.\n{init_msg}\n🔐 {pass_msg}"

    except Exception as e:
        return False, f"Kesalahan saat install MySQL: {e}"

def get_installed_mysql_versions():
    if not os.path.isdir(MYSQL_DIR):
        return {}

    versions = {}
    for folder_name in os.listdir(MYSQL_DIR):
        full_path = os.path.join(MYSQL_DIR, folder_name)
        if os.path.isdir(full_path) and folder_name.startswith("mysql-"):
            version = folder_name.replace("mysql-", "")
            versions[version] = full_path
    return versions

def create_mysql_ini(version):
    mysql_versions = get_installed_mysql_versions()
    mysql_path = mysql_versions.get(version)
    if not mysql_path:
        return False, f"MySQL versi {version} tidak ditemukan."

    ini_path = os.path.join(mysql_path, "my.ini")
    data_path = os.path.join(mysql_path, "data")
    tmp_path = TMP_DIR

    try:
        content = f"""
        [mysqld]
        basedir={mysql_path.replace(os.sep, '/')}
        datadir={data_path.replace(os.sep, '/')}
        port=3306
        sql_mode=NO_ENGINE_SUBSTITUTION,STRICT_TRANS_TABLES
        log_error={os.path.join(mysql_path, "mysql_error.log").replace(os.sep, '/')}
        tmpdir={tmp_path.replace(os.sep, '/')}
        """.strip()

        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True, f"my.ini berhasil dibuat untuk MySQL {version}"
    except Exception as e:
        return False, str(e)

def initialize_mysql_data(version):
    mysql_versions = get_installed_mysql_versions()
    mysql_path = mysql_versions.get(version)
    if not mysql_path:
        return False, f"MySQL versi {version} tidak ditemukan."

    data_path = os.path.join(mysql_path, "data")
    ini_path = os.path.join(mysql_path, "my.ini")
    mysqld_path = os.path.join(mysql_path, "bin", "mysqld.exe")

    if os.path.exists(data_path):
        return False, "Data MySQL sudah terinisialisasi."

    try:
        result = subprocess.run([mysqld_path, f"--defaults-file={ini_path}", "--initialize"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            return False, f"Inisialisasi gagal: {result.stderr}"

        err_log_path = None
        for file in os.listdir(data_path):
            if file.endswith(".err"):
                err_log_path = os.path.join(data_path, file)
                break

        if err_log_path and os.path.isfile(err_log_path):
            with open(err_log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "A temporary password is generated for root@localhost" in line:
                        temp_pass = line.strip().split(":")[-1].strip()
                        return True, f"Data berhasil diinisialisasi.\n🔐 Password root sementara: `{temp_pass}`"

        return True, "Data berhasil diinisialisasi (password root tidak ditemukan di log)."

    except Exception as e:
        return False, f"Gagal inisialisasi MySQL: {e}"
    
def change_mysql_root_password(version, new_password="mysql"):
    mysql_versions = get_installed_mysql_versions()
    mysql_path = mysql_versions.get(version)
    if not mysql_path:
        return False, f"MySQL versi {version} tidak ditemukan."

    data_path = os.path.join(mysql_path, "data")

    err_log_path = None
    for file in os.listdir(data_path):
        if file.endswith(".err"):
            err_log_path = os.path.join(data_path, file)
            break

    if not err_log_path or not os.path.isfile(err_log_path):
        return False, "File log error MySQL tidak ditemukan untuk ambil password sementara."

    temp_password = None
    with open(err_log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "A temporary password is generated for root@localhost" in line:
                temp_password = line.strip().split(":")[-1].strip()
                break

    if not temp_password:
        return False, "Password sementara tidak ditemukan di log."

    mysqladmin_path = os.path.join(mysql_path, "bin", "mysqladmin.exe")

    try:
        result = subprocess.run([
            mysqladmin_path,
            "-u", "root",
            f"-p{temp_password}",
            "password", new_password
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            return True, f"✅ Password root berhasil diubah menjadi: `{new_password}`"
        else:
            return False, f"Gagal ubah password: {result.stderr.strip()}"

    except Exception as e:
        return False, f"Error saat mengganti password root: {e}"

# PHP Management
def get_installed_php_versions():
    if not os.path.isdir(PHP_DIR):
        return {}
    versions = {}
    for folder_name in os.listdir(PHP_DIR):
        full_path = os.path.join(PHP_DIR, folder_name)
        if os.path.isdir(full_path) and folder_name.startswith("php-"):
            version = folder_name.replace("php-", "")
            versions[version] = full_path
    return versions

def update_php_ini_session_path(php_ini_path):
    try:
        with open(php_ini_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated_lines = []
        updated = False
        for line in lines:
            if line.strip().startswith("session.save_path"):
                updated_lines.append(f'session.save_path = "{TMP_DIR}"\n')
                updated = True
            else:
                updated_lines.append(line)

        if not updated:
            updated_lines.append(f'\nsession.save_path = "{TMP_DIR}"\n')

        with open(php_ini_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)

        return True, None
    except Exception as e:
        return False, str(e)

def update_apache_vhost_conf(apache_path, php_cgi_path):
    apache_conf_path = os.path.join(apache_path, "conf", "extra", "httpd-vhosts.conf")
    vhost_conf = f"""
    <VirtualHost *:80>
        ServerName localhost
        DocumentRoot "{WWW_DIR.replace(os.sep, '/')}"

        <Directory "{WWW_DIR.replace(os.sep, '/')}">
            Options +ExecCGI
            AllowOverride All
            Require all granted
        </Directory>

        <FilesMatch \\.php$>
            SetHandler fcgid-script
            FcgidWrapper "{php_cgi_path.replace(os.sep, '/')}" .php
        </FilesMatch>

        ErrorLog "logs/localhost-error.log"
        CustomLog "logs/localhost-access.log" common
    </VirtualHost>
    """
    try:
        with open(apache_conf_path, "w", encoding="utf-8") as f:
            f.write(vhost_conf.strip())
        return True, None
    except Exception as e:
        return False, str(e)

def switch_php(version):
    installed_versions = get_installed_php_versions()
    if version not in installed_versions:
        return False, f"Versi PHP {version} tidak ditemukan!"

    php_path = installed_versions[version]
    php_ini = os.path.join(php_path, "php.ini")
    php_cgi = os.path.join(php_path, "php-cgi.exe")

    if not os.path.isfile(php_ini):
        return False, f"File php.ini tidak ditemukan di {php_ini}"
    if not os.path.isfile(php_cgi):
        return False, f"File php-cgi.exe tidak ditemukan di {php_cgi}"

    # Pastikan tmp dir ada
    os.makedirs(TMP_DIR, exist_ok=True)

    # Update session path di php.ini
    success, err = update_php_ini_session_path(php_ini)
    if not success:
        return False, f"Gagal update session.save_path di php.ini: {err}"

    # Cari Apache aktif
    apache_versions = get_installed_apache_versions()
    apache_version = active_versions.get("apache")
    apache_path = apache_versions.get(apache_version)

    if not apache_path:
        return False, "Apache versi aktif tidak ditemukan. Pastikan Apache sudah dijalankan."

    # Update apache vhost config
    success, err = update_apache_vhost_conf(apache_path, php_cgi)
    if not success:
        return False, f"Gagal update httpd-vhosts.conf: {err}"

    # Restart Apache
    stop_apache()
    start_apache(apache_version)

    active_versions["php"] = version

    return True, f"Berhasil switch ke PHP {version} dan restart Apache"

def download_and_extract_php(version):
    if version not in PHP_DOWNLOAD_LINKS:
        return False, f"Link untuk PHP {version} tidak tersedia."

    url = PHP_DOWNLOAD_LINKS[version]
    target_dir = os.path.join(PHP_DIR, f"php-{version}")
    zip_path = os.path.join(PHP_DIR, f"php-{version}.zip")

    if os.path.isdir(target_dir):
        return False, f"Versi PHP {version} sudah ada."

    os.makedirs(PHP_DIR, exist_ok=True)

    try:
        success, err = download_with_progress(url, zip_path)
        if not success:
            return False, f"Gagal download PHP: {err}"
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        os.remove(zip_path)

        ini_dev = os.path.join(target_dir, "php.ini-development")
        ini_prod = os.path.join(target_dir, "php.ini-production")
        ini_dest = os.path.join(target_dir, "php.ini")

        if not os.path.exists(ini_dest):
            if os.path.exists(ini_dev):
                os.rename(ini_dev, ini_dest)
            elif os.path.exists(ini_prod):
                os.rename(ini_prod, ini_dest)
            else:
                return False, "php.ini tidak ditemukan dan tidak bisa dibuat (development/production tidak tersedia)."

        return True, f"PHP {version} berhasil diunduh, diekstrak, dan php.ini berhasil dibuat."
    except Exception as e:
        return False, f"Gagal download atau ekstrak PHP: {e}"

# ============================
# Log Read Functions
# ============================
def read_log_file(path, lines=100):
    if not os.path.isfile(path):
        return f"Log file tidak ditemukan: {path}"
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.readlines()
        return ''.join(content[-lines:])
    except Exception as e:
        return f"Gagal membaca log: {e}"

def read_apache_log():
    version = active_versions.get("apache")
    if not version:
        return "Apache tidak aktif."

    apache_versions = get_installed_apache_versions()
    apache_path = apache_versions.get(version)
    if not apache_path:
        return f"Folder Apache untuk versi {version} tidak ditemukan."

    log_path = os.path.join(apache_path, "logs", "localhost-error.log")
    return read_log_file(log_path)

def read_mysql_log():
    version = active_versions.get("mysql")
    if not version:
        return "MySQL tidak aktif."
    mysql_versions = get_installed_mysql_versions()
    path = os.path.join(mysql_versions.get(version, ""), "mysql_error.log")
    return read_log_file(path)

# ============================
# Network Speed Test
# ============================
def check_network_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download()
        upload = st.upload()
        ping = st.results.ping

        return True, {
            "ping": f"{ping:.2f} ms",
            "download": f"{download / 1_000_000:.2f} Mbps",
            "upload": f"{upload / 1_000_000:.2f} Mbps",
        }
    except Exception as e:
        return False, f"Gagal mengukur kecepatan internet: {e}"

# ============================
# progressbar download file
# ============================
def download_with_progress(url, dest_path, chunk_size=8192):
    try:
        with urllib.request.urlopen(url) as response:
            total_length = response.getheader('Content-Length')
            total_length = int(total_length) if total_length else None

            downloaded = 0
            with open(dest_path, 'wb') as out_file:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)

                    # Cetak progress ke terminal/log (opsional)
                    if total_length:
                        percent = downloaded * 100 / total_length
                        print(f"\r📥 Downloading: {percent:.2f}% ({downloaded}/{total_length} bytes)", end="")
            
            print("\n✅ Download selesai.")
        return True, None
    except Exception as e:
        return False, str(e)

# ============================
# Routes Flask
# ============================
@app.route("/")
def index():
    php_versions = get_installed_php_versions()
    apache_versions = get_installed_apache_versions()
    mysql_versions = get_installed_mysql_versions()

    apache_log = read_apache_log()
    mysql_log = read_mysql_log()

    return render_template("index.html",
                           php_versions=php_versions.keys(),
                           apache_versions=apache_versions.keys(),
                           mysql_versions=mysql_versions.keys(),
                           active_versions=active_versions,
                           service_status=service_status,
                           apache_log=apache_log,
                           mysql_log=mysql_log,
                           network_speed=network_speed_result,
                           php_download_links=PHP_DOWNLOAD_LINKS,
                           mysql_download_links=MYSQL_DOWNLOAD_LINKS,
                           apache_download_links=APACHE_DOWNLOAD_LINKS)

@app.route("/install_php", methods=["POST"])
def web_install_php():
    version = request.form.get("php_version")
    if not version:
        flash("Versi PHP tidak valid", "error")
        return redirect(url_for("index"))

    success, msg = download_and_extract_php(version)
    flash(msg, "success" if success else "error")
    return redirect(url_for("index"))

@app.route("/switch_php", methods=["POST"])
def web_switch_php():
    version = request.form.get("php_version")
    if not version:
        flash("Versi PHP tidak valid", "error")
        return redirect(url_for("index"))

    success, msg = switch_php(version)
    flash(msg, "success" if success else "error")
    return redirect(url_for("index"))

@app.route("/start_apache", methods=["POST"])
def web_start_apache():
    version = request.form.get("apache_version")
    if not version:
        flash("Versi Apache tidak valid", "error")
        return redirect(url_for("index"))

    success, msg = start_apache(version)
    flash(msg, "success" if success else "error")
    return redirect(url_for("index"))

@app.route("/stop_apache", methods=["POST"])
def web_stop_apache():
    success, msg = stop_apache()
    flash(msg, "success" if success else "error")
    return redirect(url_for("index"))

@app.route("/install_apache", methods=["POST"])
def web_install_apache():
    version = request.form.get("apache_version")
    if not version:
        flash("Versi Apache tidak valid", "error")
        return redirect(url_for("index"))

    success, msg = download_and_extract_apache(version)
    flash(msg, "success" if success else "error")
    return redirect(url_for("index"))

@app.route("/start_mysql", methods=["POST"])
def web_start_mysql():
    version = request.form.get("mysql_version")
    success, msg = start_mysql(version)
    flash(msg, "success" if success else "error")
    return redirect(url_for("index"))

@app.route("/stop_mysql", methods=["POST"])
def web_stop_mysql():
    success, msg = stop_mysql()
    flash(msg, "success" if success else "error")
    return redirect(url_for("index"))

@app.route("/install_mysql", methods=["POST"])
def web_install_mysql():
    version = request.form.get("mysql_version")
    if not version:
        flash("Versi MySQL tidak valid", "error")
        return redirect(url_for("index"))

    success, msg = download_and_extract_mysql(version)
    flash(msg, "success" if success else "error")
    return redirect(url_for("index"))

@app.route("/check_speed", methods=["POST"])
def web_check_speed():
    global network_speed_result
    success, result = check_network_speed()
    if success:
        network_speed_result = result
        flash("✅ Berhasil cek kecepatan internet.", "success")
    else:
        network_speed_result = {}
        flash(result, "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Gunakan debug=False di production
    app.run(debug=True)
    