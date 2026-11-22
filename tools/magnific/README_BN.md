# Magnific Contributor — ছবি পরীক্ষা + metadata CSV (ফ্রি tool)

Magnific-এ contributor upload-এর কোনো API নেই। তাই এই tool upload করে না; সময় বাঁচায় সবচেয়ে কষ্টের অংশে: **title, keyword, category, CSV**।

## প্রথমবার একবারই (ফ্রি Gemini key Mac-এর Keychain-এ রাখা)
1. https://aistudio.google.com/apikey থেকে ফ্রি API key বানান (Google অ্যাকাউন্ট লাগে, কার্ড লাগে না)।
2. Terminal-এ এটা চালান, key চাইলে paste করুন (chat-এ নয়):
```
security add-generic-password -s pickixo-gemini -a gemini -w
```
খরচ: $0 (Gemini ফ্রি টিয়ার)। মিনিটে ~১০টা ছবি, দিনে কয়েকশো পর্যন্ত; tool নিজেই গতি সামলায়।

## প্রতিবার
1. ভালো ছবিগুলো একটা ফোল্ডারে রাখুন, যেমন `~/Desktop/magnific_batch` (খারাপ হাত/মুখ/লেখা থাকা ছবি নিজে বাদ দিন)।
2. চালান:
```
cd ~/Desktop/Amazon && tools/magnific/run.sh ~/Desktop/magnific_batch --model-name "Midjourney"
```
   (যেটা দিয়ে বানিয়েছেন সেটার নাম দিন। শুধু size/duplicate দেখতে: `--check-only`)
3. ফোল্ডারে `upload_jpg/` তৈরি হবে (Magnific photo শুধু JPG নেয়) — **এই ফোল্ডারের JPG আর তার ভেতরের CSV-ই upload করবেন**। আর:
   - `magnific_metadata.csv` — upload-এর জন্য
   - `magnific_report.txt` — কোন ছবি ছোট / প্রায় একই / সমস্যা আছে (এগুলো বাদ দিন বা ঠিক করুন)
4. contributor.magnific.com → **Upload** → ছবিগুলো drag & drop → **CSV upload** → কয়েকটা title দেখে নিন → **AI-generated চিহ্ন** আছে কিনা দেখুন → **Submit**।

## ছোট ছবি নিজে থেকে upscale (Upscayl)
- https://upscayl.org থেকে Upscayl install করুন (Applications ফোল্ডারে)।
- তারপর tool নিজেই ছোট ছবি খুঁজে: **4x বড় করে আবার 2048px-এ ছোট করে** (supersampling — সোজা 2x-এর চেয়ে পরিষ্কার), `<নাম>_up.jpg` বানায়, তারপর মান যাচাই করে।
- **Upload করবেন `_up.jpg` ফাইলটা**, আসলটা নয় (CSV-তে সেই নামই থাকে)।
- বাস্তবধর্মী model আগে বাছে (high-fidelity / standard), "digital art" নয়।
- upscale না চাইলে: `--no-upscale`
- মনে রাখবেন: upscale শুধু সহজ ছবিতে (background, কম জিনিস, প্রকৃতি) ভালো কাজ করে; মানুষ/খাবারের ক্লোজআপে প্রায়ই "Low quality" হয়। সেরা উপায় এখনও Firefly-তে বড় সাইজে বানানো।

## মনে রাখবেন
- CSV-র column নাম (`Filename;Title;Keywords;Prompt;Model`) Magnific-এর Upload পেজের CSV template-এর সাথে একবার মিলিয়ে নিন; আলাদা হলে `magnific_meta.py`-তে `HEADER` বদলান (বা আমাকে বলুন)।
- প্রতিটা keyword তালিকায় `_ai_generated` থাকে।
- ৫০০টা ফাইল প্রকাশ হলে SFTP (`uploads.magnific.com`, port 60022) খুলবে; তখন upload-ও automate করা যাবে।

## এক ক্লিকে (Magnific Batch app)
1. অ্যাডমিনে Image ideas → **🎨 Copy + open Firefly** → Firefly-তে Cmd+V → বড় সাইজে বানান → ভালো ছবিগুলো Download করুন।
2. Mac-এর Desktop-এ **Magnific Batch** app-এ double-click। এটা Downloads থেকে `Firefly…` নামের ছবিগুলো `~/Desktop/Magnific/<তারিখ>/`-এ নেয়, চেক করে, title/keyword/CSV বানায়, তারপর upload ফোল্ডার আর Magnific খুলে দেয়।
3. Magnific-এ JPG + CSV drag করুন → AI চিহ্ন → Submit।
প্রথমবার macOS "Downloads ফোল্ডারে access" চাইতে পারে: Allow দিন। App হারালে আবার বানান: `tools/magnific/make_app.sh`
