# Devam notu — oturumlar arası süreklilik

Bu dosya bir **koşum kaydıdır** (`.claude/olcum_kutugu.json` gibi): depodan
yeniden üretilemez, git'e girer. Amaç: bir oturum bitince "kaldığın yer"in
kaybolmaması. Sonraki oturum — taze klon, taze konteyner olsa bile —
`.claude/hooks/session-start.sh` bu dosyanın içeriğini otomatik olarak
bağlama enjekte eder. Yani bunu okumak için ayrı bir komut çalıştırmana
gerek yok; oturum başında zaten önündedir.

**Bu bir hafıza DEĞİL, bir el notudur.** Claude'un "düşünceleri" aynı kalmaz;
burada yazan, bir sonraki oturumun sıfırdan keşfetmeden devam edebilmesi
için bırakılmış kısa bir özet ve nedendir.

## Kural

- Bir işi **yarım bırakıyorsan** (oturum sonu, uzun görev arası, kullanıcı
  "dur"/"devam ederiz" dediğinde) bu dosyanın "Şu an" bölümünü GÜNCELLE.
- Üç satır yeter: **Şu an neredeyiz**, **Sıradaki adım**, **Neden böyle**
  (kısa — asıl gerekçe kod/commit mesajında zaten var, burada yalnızca
  bir sonraki oturumun hangi commit'e/dala bakması gerektiğini söyle).
- Eski "Şu an" girdisi silinmez, **Geçmiş** bölümüne düşer; orada en fazla
  son 5 girdi tutulur, daha eskisi atılır (günlük değil, devam kartı).
- Buraya gizli/kişisel veri, token, şifre yazma — bu dosya depoya girer.
- Graf kanıt değildir kuralı burada da geçerli: bu not bir **niyet/durum**
  kaydıdır, çalışan koddan veya commit geçmişinden üstün değildir.
  Çelişkide commit/kod kazanır.

## Şu an (en güncel)

**2026-09-13 — dal `claude/project-history-521-commits-bl5e4o`**

- Şu an neredeyiz: `docs/PROJE_GECMISI.md` yazıldı (521 commit, ilk
  commit'ten HEAD'e kronolojik, hash+tarih+mesaj+stat) ve push edildi.
  Ardından bu dosya + `session-start.sh` güncellemesi ile "oturumlar arası
  süreklilik" mekanizması kuruldu.
- Sıradaki adım: kullanıcı onaylarsa bu değişiklikleri commit'leyip aynı
  dala push et. PR açılmadı — kullanıcı istemedikçe açma.
- Neden böyle: kullanıcı "session bitse bile kaldığın yerden devam edebilen
  bir sistem" istedi. Gerçek bir "hafıza" kurulamıyor (her oturum sıfırdan
  başlıyor); bunun yerine mevcut bilgi-grafı deseni (git'e giren dosya +
  SessionStart hook ile otomatik enjeksiyon) bu amaca uyarlandı.

## Geçmiş girdiler

(yok — ilk girdi yukarıda)
