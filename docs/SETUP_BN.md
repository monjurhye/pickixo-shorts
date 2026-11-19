# Pickixo Shorts: সেটআপ গাইড (একবারই করতে হবে)

এই ধাপগুলো শেষ হলে সিস্টেম প্রতিদিন নিজে থেকে চলবে। Mac চালু রাখার দরকার নেই।

## যা যা কী করে
| অংশ | কোথায় চলে | কাজ |
|---|---|---|
| `pipeline/` | GitHub Actions (রোজ ১৩:০০ UTC) | Claude দিয়ে script লেখা ও যাচাই → Pexels ক্লিপ → ভিডিও → YouTube এ upload |
| `site/` | Cloudflare Pages | shop.pickixo.com, যেখানে প্রতিটা ভিডিওর প্রোডাক্টের লিংক থাকে |
| `tools/youtube_authorize.py` | আপনার Mac এ, একবার | প্রতিটা চ্যানেলের YouTube অনুমতি GitHub এ সেভ করে |

গোপন চাবি কোনো ফাইলে থাকে না। সব থাকে **GitHub Secrets** এ।

---

## ধাপ ১: GitHub repo (আমি বানিয়ে দিতে পারি)
Private repo `pickixo-shorts` তৈরি করে কোড push করা হবে।

## ধাপ ২: তিনটা key → GitHub Secrets
Repo খুলুন: **Settings → Secrets and variables → Actions → New repository secret**

| Secret এর নাম | কোথা থেকে পাবেন |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `PEXELS_API_KEY` | pexels.com/api (ফ্রি) |

Key কখনো chat বা কোনো ফাইলে লিখবেন না।

## ধাপ ৩: Google Cloud এ YouTube API (একবার, প্রায় ১০ মিনিট)
1. console.cloud.google.com এ একটা নতুন project খুলুন, যেমন `pickixo-shorts`।
2. **APIs & Services → Library** থেকে **YouTube Data API v3** চালু (Enable) করুন।
3. **OAuth consent screen** এ যান:
   - User type: **External**
   - App name দিন, আর ইমেইলের ঘরে আপনার ইমেইল দিন।
   - Scopes: `youtube.upload` আর `youtube.readonly`
   - ⚠️ শেষে **"Publish app" → In production** করুন। Testing mode এ থাকলে অনুমতি **৭ দিন পর বাতিল** হয়ে যায়। নিজের ব্যবহারের জন্য Google এর verification লাগে না, শুধু Allow দেওয়ার সময় একটা সতর্কবার্তা দেখাবে।
4. **Credentials → Create credentials → OAuth client ID → Desktop app** বানান। Client ID আর Secret পরের ধাপে লাগবে।

## ধাপ ৪: ২০টা চ্যানেলে অনুমতি দেওয়া (Mac এ, চ্যানেল প্রতি ~১ মিনিট)
```bash
cd ~/Desktop/Amazon
python3 tools/youtube_authorize.py ch01
```
- প্রথমবার Client ID আর Secret চাইবে। Secret টাইপ করার সময় স্ক্রিনে দেখা যাবে না।
- Browser খুলবে। **ch01 এর niche এর জন্য যে চ্যানেল চান** সেটা বেছে **Allow** চাপুন।
- স্ক্রিপ্ট নিজেই অনুমতিটা GitHub এ সেভ করবে আর চ্যানেলটা চালু করে দেবে।
- একইভাবে `ch02` … `ch20` চালান। কোন চ্যানেলের কোন niche, তা `config/channels.json` এ লেখা আছে।
- শেষে `config/channels.json` commit করে push করুন (আমিও করে দিতে পারি)।

## ধাপ ৫: Cloudflare Pages → shop.pickixo.com
1. Cloudflare dashboard এ যান: **Workers & Pages → Create → Pages → Connect to Git**, তারপর `pickixo-shorts` repo বেছে নিন।
2. Build settings:
   - Build command: `python3 site/build.py`
   - Output directory: `public`
3. Deploy হয়ে গেলে **Custom domains → `shop.pickixo.com`** যোগ করুন। pickixo.com Cloudflare এ আছে বলে DNS নিজে থেকেই হয়ে যাবে।

এতে pickixo.com এর মূল সাইটে কোনো পরিবর্তন হয় না।

## ধাপ ৬: ইমেইল রিপোর্ট
প্রতিদিন GitHub একটা issue খোলে "Pickixo daily report — তারিখ" নামে, আর GitHub সেটা আপনাকে ইমেইল করে।
- GitHub → Settings → Emails এ **monjurhye@gmail.com** যোগ করে primary বানান।
- GitHub → Settings → Notifications এ **Email** চালু রাখুন।

## ধাপ ৭: প্রথম পরীক্ষা
Repo খুলুন: **Actions → Daily Shorts → Run workflow**
- প্রথমবার **dry_run ✅** দিয়ে চালান। Upload হবে না, ভিডিওটা Artifacts এ পাওয়া যাবে।
- তারপর **channel = ch01** দিয়ে (dry_run ছাড়া) চালান। একটা আসল ভিডিও upload হবে।
- সব ঠিক থাকলে আর কিছু করতে হবে না। প্রতিদিন নিজে থেকে চলবে।

---

## 🛑 সব থামানো (STOP)
Repo খুলুন: **Settings → Secrets and variables → Actions → Variables**। সেখানে `PAUSED` নামে একটা variable বানিয়ে মান দিন `true`। আবার চালু করতে মান দিন `false`।

## 🛡️ নিরাপত্তা ব্যবস্থা (কোডে আগে থেকেই আছে)
- প্রতিটা script এর জন্য দ্বিতীয়বার Claude ডাকা হয়। দাম, মিথ্যা urgency, স্বাস্থ্যের দাবি বা ভুল তথ্য পেলে ভিডিও বাদ যায়।
- ভিডিওতে কোনো দাম বা Amazon এর ছবি থাকে না। লিংক যায় Amazon search এ, `tag=monjur09-20` সহ।
- প্রতিটা চ্যানেলের niche আলাদা, আর একই topic বা ক্লিপ বারবার আসে না।
- কোনো চ্যানেলে পরপর ২ বার upload এ সমস্যা হলে (403 বা অনুমতি বাতিল) সেই চ্যানেল **নিজে থেকে বন্ধ** হয়, আর রিপোর্টে জানানো হয়। আবার চালু করতে `data/state.json` এ ওই চ্যানেলের `auto_disabled` এর মান `false` করুন।
- YouTube এর strike বা warning API দিয়ে জানা যায় না। তাই YouTube থেকে আসা ইমেইল নিজে দেখবেন।

## 💰 খরচের হিসাব
- GitHub Actions: private repo তে মাসে ২,০০০ ফ্রি মিনিট। ২০টা চ্যানেলে দিনে ~৪০–৬০ মিনিট লাগে, মাসে ~১,২০০–১,৮০০ মিনিট। সীমা ছাড়িয়ে গেলে repo public করলে ফ্রি থাকবে, কারণ Secrets তখনও গোপন থাকে।
- Claude (Opus 5.5, $4/$20 প্রতি ১০ লাখ token): প্রতি ভিডিওতে ~$০.০৫–০.১০, তাই ৬০০ ভিডিওতে মাসে ~$৩০–৬০। খরচ কমাতে চাইলে `config/settings.json` এ `"model": "claude-haiku-5-5"` দিন (~১০ গুণ সস্তা, তবে লেখার মান কিছুটা কম হতে পারে)।
- Pexels, Cloudflare Pages: ফ্রি।
