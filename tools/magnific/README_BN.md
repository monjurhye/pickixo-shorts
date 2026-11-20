# Magnific Contributor — ছবি পরীক্ষা + metadata CSV (ফ্রি tool)

Magnific-এ contributor upload-এর কোনো API নেই। তাই এই tool upload করে না; সময় বাঁচায় সবচেয়ে কষ্টের অংশে: **title, keyword, category, CSV**।

## প্রথমবার একবারই (OpenAI key Mac-এর Keychain-এ রাখা)
Terminal-এ এটা চালান, key চাইলে paste করুন (chat-এ নয়):
```
security add-generic-password -s pickixo-openai -a openai -w
```
খরচ: প্রতি ছবিতে প্রায় $0.001 (১০০০ ছবিতে ~$1)।

## প্রতিবার
1. ভালো ছবিগুলো একটা ফোল্ডারে রাখুন, যেমন `~/Desktop/magnific_batch` (খারাপ হাত/মুখ/লেখা থাকা ছবি নিজে বাদ দিন)।
2. চালান:
```
cd ~/Desktop/Amazon && tools/magnific/run.sh ~/Desktop/magnific_batch --model-name "Midjourney"
```
   (যেটা দিয়ে বানিয়েছেন সেটার নাম দিন। শুধু size/duplicate দেখতে: `--check-only`)
3. ফোল্ডারে দুটো ফাইল হবে:
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
