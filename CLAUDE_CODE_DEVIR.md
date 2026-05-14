# Claude Code Devir Talimatı

Bu repo'yu Claude Code'a verirken kullanılacak ilk prompt.

---

## İlk mesaj (Claude Code'a)

```
Bu projeyi geliştireceksin. Önce şu dosyaları sırasıyla oku ve özetini bana ver:

1. /PROJE_BRIEF.md
2. /docs/KARARLAR.md
3. /docs/HESAPLAMA_MOTORU.md
4. /docs/TRENDYOL_API_NOTLAR.md

Sonra mevcut iskeleti incele (backend/ klasörünü kazıyarak).

Bana şunları söyle:
- Projeyi doğru anladığını teyit eden 2-3 cümle
- Faz 0 (Setup) için tam adım listesi
- Soru veya belirsizliklerin varsa

Beklemeden Faz 0'a başlama. Önce planı sun, onayımı al.

Review-driven mode kullan. Her adımda küçük checkpoint'lerle ilerle.
Türkçe yorum yazabilirsin ama kod (değişken, fonksiyon, commit mesajı) İngilizce.
```

---

## Devam ederken kullanacağın kalıplar

**Faz onayı:**
> "Faz X'e geçmeden önce mevcut durumu özetle ve onayımı al."

**Test-first hatırlatması:**
> "Hesaplama motorunda TDD yapıyoruz. Önce test, sonra implementasyon."

**Mimari kuralı ihlali fark edersen:**
> "Bu hesaplama motorunda 'trendyol' kelimesi geçiyor. ADR-004 ihlali. Düzelt."

**Belirsizlik:**
> "Bu konuda emin değilim, sen ne öneriyorsun? İki seçenek varsa karşılaştır."
