# আয়-ব্যয়ের হিসাব (Earnings) — পরে করার কাজ

সংরক্ষণ: ২১ নভেম্বর ২০২৬। কোড লাইভে আছে (commit `48b8c8f`), শুধু নিচের সেটআপ বাকি।

## এখন কী অবস্থা

**shop.pickixo.com/admin → 💰 Earnings** (মেনুর সবার শেষে)

| উৎস | কীভাবে আসে | অবস্থা |
|---|---|---|
| AppSumo (Impact) | রোজ API থেকে | চালু |
| AliExpress | রোজ API থেকে | চালু |
| AdBlueMedia | প্রতিটা lead-এ সাথে সাথে (postback) | কোড চালু, **লিংক বসানো বাকি** |
| OpenAI খরচ | রোজ OpenAI Costs API থেকে | কোড চালু, **admin key বাকি** |
| Anthropic খরচ | রোজ Admin API থেকে | দরকার নেই (প্রজেক্ট এখন Anthropic ব্যবহার করে না) |
| Amazon, Magnific, Facebook | API নেই | হাতে লিখতে হবে (Add income) |

সব ফ্রি, কোনো API খরচ নেই।

## বাকি কাজ ১: AdBlueMedia postback

1. /admin → Earnings → নিচে **"AdBlueMedia postback (one-time setup)"** বক্স।
2. বক্সে ক্লিক করে পুরো লিংক কপি করুন (এতে গোপন key আছে, কাউকে দেবেন না)।
3. AdBlueMedia → Tools / Postback → লিংক বসিয়ে Save।
4. লিংকে `{payout}` আর `{lead_id}` আছে। AdBlueMedia-তে এদের নাম আলাদা হলে শুধু `{ }`-এর ভেতরেরটা বদলাবেন।

## বাকি কাজ ২: OpenAI admin key

1. platform.openai.com/settings/organization/admin-keys → **Create new admin key** → Read only।
2. `sk-admin-…` key কপি করুন।
3. Terminal-এ চালান, key চাইলে paste করে Enter:

```bash
cd ~/Desktop/Amazon && gh secret set OPENAI_ADMIN_KEY
```

4. পরের Daily Pins রান থেকে OpenAI খরচ নিজে আসবে।
   "Monthly fixed cost"-এ OpenAI আলাদা করে লিখবেন না, তাহলে দুবার গোনা হবে।

## হাতে লেখার নিয়ম

- Amazon Associates, Magnific, Facebook-এর আয় → **Add income** (তারিখ, সাইট, ডলার)।
- Domain/hosting, Buffer ইত্যাদি → **Monthly fixed cost** (যদি টাকা লাগে)।
- AppSumo, AliExpress, AdBlueMedia, OpenAI হাতে লিখবেন না, এগুলো নিজে আসে।

## কোড কোথায়

- `pipeline/earnings.py` — Impact, AliExpress, OpenAI/Anthropic খরচ সংগ্রহ (Daily Pins workflow-এর সাথে চলে)
- `functions/api/postback/[source].js` — AdBlueMedia postback গ্রহণ
- `lib/earnings.js` — হিসাব জমা রাখা (Cloudflare KV)
- `functions/admin/index.js` — Earnings ট্যাব
