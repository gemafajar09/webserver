from flask import Flask, render_template, request, redirect, url_for, flash
import subprocess
import os
import speedtest

app = Flask(__name__)
app.secret_key = "secret-key-1234"
network_speed_result = {}

PHP_VERSIONS = {
    # "7.4": "D:\server\php\php-7.4.33-nts-Win32-vc15-x64",
    # "8.0": "D:\server\php\php-8.0.30-nts-Win32-vs16-x64",
    # "8.1": "D:\server\php\php-8.1.33-nts-Win32-vs16-x64",
    "8.2": "D:\server\php\php-8.2.29-nts-Win32-vs16-x64",
    "8.3": "D:\server\php\php-8.3.24-nts-Win32-vs16-x64",
    "8.4": "D:\server\php\php-8.4.11-nts-Win32-vs17-x64",
}

APACHE_VERSIONS = {
    "2.4": "D:/server/apache/Apache24",
}

MYSQL_PATH = "D:/server/mysql/mysql-8.4.3-winx64"

service_status = {
    "apache": False,
    "mysql": False,
}

active_versions = {
    "php": None,
    "apache": None,
}

def switch_php(version):
    if version not in PHP_VERSIONS:
        return False, f"Versi PHP {version} tidak ditemukan!"

    success, msg = set_active_php_version(version)
    if not success:
        return False, msg

    stop_apache("2.4")
    start_apache("2.4")

    active_versions["php"] = version
    return True, f"Berhasil switch ke PHP {version} dan restart Apache"

def start_apache(version):
    if version not in APACHE_VERSIONS:
        return False, f"Versi Apache {version} tidak ditemukan!"
    apache_bin = os.path.join(APACHE_VERSIONS[version], "bin", "httpd.exe")
    if not os.path.exists(apache_bin):
        return False, "Apache executable tidak ditemukan!"
    subprocess.Popen([apache_bin])
    service_status["apache"] = True
    active_versions["apache"] = version
    return True, f"Apache {version} started"

def stop_apache(version):
    subprocess.run(["taskkill", "/F", "/IM", "httpd.exe"])
    service_status["apache"] = False
    active_versions["apache"] = None
    return True, f"Apache {version} stopped"

def start_mysql():
    mysql_bin = os.path.join(MYSQL_PATH, "bin", "mysqld.exe")
    if not os.path.exists(mysql_bin):
        return False, "MySQL executable tidak ditemukan!"
    subprocess.Popen([mysql_bin])
    service_status["mysql"] = True
    return True, "MySQL started"

def stop_mysql():
    subprocess.run(["taskkill", "/F", "/IM", "mysqld.exe"])
    service_status["mysql"] = False
    return True, "MySQL stopped"
    
def set_active_php_version(version):
    if version not in PHP_VERSIONS:
        return False, f"Versi PHP {version} tidak ditemukan!"

    php_path = PHP_VERSIONS[version]
    php_ini = os.path.join(php_path, "php.ini")
    session_path = "D:/server/tmp"

    # Pastikan php.ini ada
    if not os.path.exists(php_ini):
        return False, f"php.ini tidak ditemukan di {php_ini}"

    # Pastikan folder session_path ada
    if not os.path.exists(session_path):
        try:
            os.makedirs(session_path)
        except Exception as e:
            return False, f"Gagal membuat folder session path: {e}"

    # Update session.save_path di php.ini
    try:
        with open(php_ini, "r", encoding="utf-8") as f:
            lines = f.readlines()

        with open(php_ini, "w", encoding="utf-8") as f:
            for line in lines:
                if line.strip().startswith("session.save_path"):
                    f.write(f'session.save_path = "{session_path}"\n')
                else:
                    f.write(line)
    except Exception as e:
        return False, f"Gagal update session.save_path di php.ini: {e}"

    # Update konfigurasi virtual host Apache
    php_cgi = os.path.join(php_path, "php-cgi.exe").replace("\\", "/")
    conf_path = os.path.join(APACHE_VERSIONS["2.4"], "conf", "extra", "httpd-vhosts.conf")

    vhost_conf = f"""
    <VirtualHost *:80>
        ServerName localhost
        DocumentRoot "D:/server/www"

        <Directory "D:/server/www">
            Options +ExecCGI
            AllowOverride All
            Require all granted
        </Directory>

        <FilesMatch \\.php$>
            SetHandler fcgid-script
            FcgidWrapper "{php_cgi}" .php
        </FilesMatch>

        ErrorLog "logs/localhost-error.log"
        CustomLog "logs/localhost-access.log" common
    </VirtualHost>
    """

    try:
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(vhost_conf.strip())
    except Exception as e:
        return False, f"Gagal update httpd-vhosts.conf: {e}"

    return True, f"PHP {version} aktif dan konfigurasi VirtualHost serta session path berhasil diperbarui"

def read_apache_log():
    try:
        log_path = os.path.join(APACHE_VERSIONS["2.4"], "logs", "localhost-error.log")
        if not os.path.exists(log_path):
            return "Log file Apache tidak ditemukan."
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            return ''.join(f.readlines()[-100:])
    except Exception as e:
        return f"Gagal membaca Apache log: {str(e)}"

# def read_php_log():
#     try:
#         for version, path in PHP_VERSIONS.items():
#             log_file = os.path.join(path, "php_error.log")
#             if os.path.exists(log_file):
#                 with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
#                     return ''.join(f.readlines()[-100:])
#         return "Log file PHP tidak ditemukan."
#     except Exception as e:
#         return f"Gagal membaca PHP log: {str(e)}"
    
def read_mysql_log():
    try:
        log_path = os.path.join(MYSQL_PATH, "./", "mysql_error.log")
        if not os.path.exists(log_path):
            return "Log file MySQL tidak ditemukan."
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            return ''.join(f.readlines()[-100:])
    except Exception as e:
        return f"Gagal membaca MySQL log: {str(e)}"

def check_network_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download()
        upload_speed = st.upload()
        ping = st.results.ping

        # Format hasil dalam Mbps
        result = {
            "ping": f"{ping:.2f} ms",
            "download": f"{download_speed / 1_000_000:.2f} Mbps",
            "upload": f"{upload_speed / 1_000_000:.2f} Mbps"
        }

        return True, result

    except Exception as e:
        return False, f"Gagal mengukur kecepatan internet: {str(e)}"
    
@app.route("/")
def index():
    apache_log = read_apache_log()
    mysql_log = read_mysql_log()

    return render_template("index.html",
                           php_versions=PHP_VERSIONS.keys(),
                           apache_versions=APACHE_VERSIONS.keys(),
                           active_versions=active_versions,
                           service_status=service_status,
                           apache_log=apache_log,
                           mysql_log=mysql_log,
                           network_speed=network_speed_result)

@app.route("/switch_php", methods=["POST"])
def web_switch_php():
    version = request.form.get("php_version")
    success, msg = switch_php(version)
    flash(msg)
    return redirect(url_for("index"))

@app.route("/start_apache", methods=["POST"])
def web_start_apache():
    version = request.form.get("apache_version")
    success, msg = start_apache(version)
    flash(msg)
    return redirect(url_for("index"))

@app.route("/stop_apache", methods=["POST"])
def web_stop_apache():
    version = active_versions["apache"] or "Unknown"
    success, msg = stop_apache(version)
    flash(msg)
    return redirect(url_for("index"))

@app.route("/start_mysql", methods=["POST"])
def web_start_mysql():
    success, msg = start_mysql()
    flash(msg)
    return redirect(url_for("index"))

@app.route("/stop_mysql", methods=["POST"])
def web_stop_mysql():
    success, msg = stop_mysql()
    flash(msg)
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
    app.run(debug=True)
