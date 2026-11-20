# Facebook page — USA-র জন্য রূপান্তর + automation

## ক) Page রূপান্তর (একবার, নিজে করবেন)
1. **পুরনো পোস্ট মুছবেন না — Archive করুন।** Page → Manage posts → পোস্ট বাছুন → **Archive** (চাইলে পরে ফেরানো যায়)। একসাথে সব মুছলে monetization review-এ সমস্যা হতে পারে, আর ফেরানো যায় না।
2. **নাম/বিবরণ English-এ, US-এর জন্য:** নাম যেমন "Frugal Home Hacks" (নাম বদল Facebook review করে, কয়েক দিন লাগতে পারে; বড় বদল হলে মাঝে মাঝে আটকে দেয়)। Category: *Home & Garden Website* / *Personal Blog*। Bio: "Simple ways to save money at home — kitchen, cleaning, organization & budget finds."
3. Profile/cover ছবি নতুন niche-এর সাথে মিলিয়ে দিন।
4. প্রথম ২–৩ সপ্তাহ reach কমতে পারে, কারণ পুরনো follower-রা নতুন বিষয়ে কম সাড়া দেয়। নিয়মিত পোস্ট দিলে US দর্শক আসতে শুরু করে।
5. **Country restriction এখনই দেবেন না** (Settings → Country restrictions) — পরে US দর্শক বাড়লে ভাববেন।

## খ) Automation চালু (Graph API — Facebook-এর অফিসিয়াল উপায়)
1. https://developers.facebook.com → **My Apps → Create App** → use case: **"Manage everything on your Page"** (না পেলে "Other → Business") → নাম `Pickixo Poster`।
2. **Tools → Graph API Explorer** → ডানে আপনার app বাছুন → **Get Token → Get Page Access Token** → permission: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` → আপনার Page বেছে Allow।
3. দীর্ঘমেয়াদি token: **Tools → Access Token Debugger** → token paste → **Extend Access Token** → নতুন (long-lived) user token কপি → Graph API Explorer-এ সেটা বসিয়ে query: `me/accounts` → Submit → আপনার Page-এর `access_token` আর `id` পাবেন (এই page token মেয়াদহীন)।
4. GitHub → Settings → Secrets → Actions → New secret:
   - `FB_PAGE_ID` = Page-এর id
   - `FB_PAGE_TOKEN` = Page-এর access_token
   (token chat-এ বা screenshot-এ দেবেন না।)
5. পরীক্ষা: GitHub → Actions → **Image Ideas** → Run workflow → **fb_check** টিক → Run। লগে Page-এর নাম দেখালে ঠিক আছে।

## যা automatic হবে
- প্রতিদিন সকাল ৮টায় (বাংলাদেশ) ৪টা পোস্টের idea: ২টা Reel script, ১টা photo/carousel, ১টা প্রশ্ন-পোস্ট।
- **Photo আর প্রশ্ন-পোস্ট** নিজে থেকেই US Eastern সময়ে Page-এ **schedule** হবে (Pexels-এর ফ্রি ছবি দিয়ে)।
- **Reel** automatic নয় — script dashboard-এ থাকবে, ভিডিও বানিয়ে নিজে পোস্ট করবেন (নিজের ভিডিও সবচেয়ে বেশি আয় করে)।
- থামাতে: GitHub repo variable `FB_PAUSED` = `true`।
