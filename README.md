# Note
untuk settingan apache silahkan buka folder **apache/apapche-2.4/conf/httpd.conf** lalu ubah **Define SRVROOT "D:/server/apache/apache-2.4"** dengan directory tempat file apache tersimpan.

# Info
jika ingin menggunakan ssl local maka silahkan download cacert.pem di link berikut :
<a href="https://curl.se/ca/cacert.pem">Download</a>

untuk menjalankan bisa langsung double klik **main.py** atau bisa ubah script **run.bat** sesuai dir tempat anda menyimpan file ini.

simpan file cacert.pem tadi kedalam dir php yag di gunakan.

contoh: D:\server\php\php-8.4\extras\ssl\

pastekan file cacert.pem kedalam folder ssl

lalu lakukan edit file php.ini
Cari Baris Berikut
```
;curl.cainfo =
;openssl.cafile =
```
dan ubah menjadi seperti ini
```
curl.cainfo = "D:\server\php\php-8.4\extras\ssl\cacert.pem"
openssl.cafile = "D:\server\php\php-8.4\extras\ssl\cacert.pem"
```

jika error terjadi pada saat pertamak lai install php dan tidak bisa login ke adminer silahkan cek file php.ini
```
extension_dir = "ext" <--- hapus tanda ;
extension=pdo_mysql <--- hapus tanda ;
extension=mysqli <--- hapus tanda ;
```
# Penampakan
![contoh sedang berjalan](https://r2.fivemanage.com/lVmArIHz1ZezfirbeEl84/Screenshot2025-08-02205635.png "Contoh runing")
