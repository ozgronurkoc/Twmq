# Sınırlar: bayatlık, boyut, gizlilik

## Bayatlık — grafın tek gerçek riski

Bilgi grafı depodan **türetilir**, yani kod her değiştiğinde bir parçası
yanlışlanır. Tehlikeli olan yanlışlanması değil, **sessizce** yanlışlanmasıdır.

Üç savunma var, güçten zayıfa:

1. **Girdi bazlı `hash`** (`git hash-object`). Dosya içeriği değişince tutmaz.
   Kesin sinyal budur; tazelik denetimi buna bakar.
2. **`git.head`** kaydı. Farklıysa graf şüphelidir — ama depoda dokunulmamış
   dosyaların girdileri hâlâ geçerlidir, o yüzden tek başına silme gerekçesi
   değildir.
3. **`yazildi` tarihi.** En zayıfı: zaman geçmesi tek başına hiçbir şeyi
   yanlışlamaz, ama okuyucuya ne kadar güvenmesi gerektiğini söyler.

Yaş için katı bir eşik **yok** — bu depoda ölçüt zaman değil, dosyanın
değişip değişmediğidir. Hash tutuyorsa altı ay önceki girdi geçerlidir; hash
tutmuyorsa dünkü girdi geçersizdir.

`sayilar` bölümünün hash'i yoktur (bir sayı tek bir dosyaya bağlı değildir),
onun denetimi `grep`'tir: kayıtlı `anildigi_yerler` hâlâ o değeri içeriyor mu.

## Bekçisi yok — bilinen ve kabul edilmiş boşluk

Bu depo iddiaları pytest bekçileriyle tutar (`backend/tests/test_belgeler.py`).
Bilgi grafının böyle bir bekçisi **yok**: tazelik denetimi elle çağrılır, CI
onu koşmaz.

Boşluk bu yüzden git dışı kalmayla kapatıldı — sürümlenmeyen bir defterin
bayatlaması yalnızca onu yazan makineyi yanlış bilgilendirir, `git pull` yapan
herkesi değil. Graf sürümlenmek istenirse önce bekçisi yazılmalıdır, sonra
`.gitignore` satırı kaldırılmalıdır; sırası tersine dönerse depo, bekçisiz bir
türetilmiş çıktı sürümlemiş olur.

## Boyut

Defter büyürse okumak pahalılaşır ve her okuma bağlam yer. Ölçü:

```bash
du -h .claude/bilgi_grafi.json
python3 -c "import json;g=json.load(open('.claude/bilgi_grafi.json'));print({k:(len(v) if isinstance(v,list) else v) for k,v in g.items()})"
```

Yüzlerce girdiye çıkarsa sorun envanterin büyüklüğü değil, **bölüm bazlı
okunmamasıdır**: tamamını yüklemek yerine ilgili bölümü sorgula
([sorgular.md](sorgular.md)).

## Gizlilik ve lisans — grafa ne girmez

* **Veri girmez.** Oran arşivi, eğitim korpusu, bülten görselleri, model
  artefaktları — hiçbirinin içeriği grafa yazılmaz. Graf yalnızca *nerede
  durduklarını*, *hangi komutun ürettiğini* ve *git dışı olup olmadıklarını*
  kaydeder.
* **StatsBomb özel durumu.** `.gitignore` gerekçesi açık: "StatsBomb Public Data
  User Agreement" md. 1.2.1 veriyi üçüncü tarafa dağıtmayı yasaklıyor ve bu depo
  public. Grafa o veriden **sayı bile** kopyalanmaz; lisansın serbest bıraktığı
  şey katsayı ve rapordur, onlar da zaten depoda kendi dosyalarında duruyor.
* **Sır girmez.** `SESSION_SECRET`, `HEALTH_ALARM_URL` gibi ortam
  değişkenlerinin **adı** envanter bilgisidir ve yazılabilir; **değeri**
  yazılmaz.
* Defter git dışı olsa da makinede düz metin durur; sır saklamak için uygun bir
  yer değildir.

## Graf ne değildir

* **Kanıt değildir.** Çelişkide sıra: çalışan ölçüm > kod > belge > graf.
* **Belgenin yerine geçmez.** `.gitignore` yorumları, `README.md` bölümleri ve
  test docstring'leri kaynaktır; graf onlara **işaret eder**, onları kopyalamaz.
  Kopyalarsa iki gerçek kaynak olur ve ikisi ayrışır.
* **Kod üretmez, kaynak kodu değiştirmez.** Yazdığı tek dosya
  `.claude/bilgi_grafi.json`.
