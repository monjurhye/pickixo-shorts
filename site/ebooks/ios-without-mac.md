# Publish an iOS App Without a Mac

**From Windows to the App Store: a complete step-by-step guide**

Codemagic · App Store Connect · AdMob · In-App Purchase · TestFlight · App Review

Written from the real experience of publishing an app. Every step of putting a real app on the App Store from nothing but a Windows computer, with no Mac and no iPhone: the steps, the mistakes, and how they were fixed.

*First edition (English) · 2026 · pickixo.com*

---

## About this edition

© 2026 Pickixo. All rights reserved. This English edition is offered free on pickixo.com. You may use the templates and code snippets in your own apps, as many as you like. Please don't resell this book or republish it elsewhere.

**Disclaimer.** The information in this book is current as of October 2026. Apple, Google and other services can change their rules, prices and free limits at any time, so check the relevant official page before you act. This book does not guarantee that any app will be approved. It is not legal or tax advice.

Apple, App Store, iPhone, iPad, Xcode and TestFlight are trademarks of Apple Inc. Google and AdMob are trademarks of Google LLC. Claude is a trademark of Anthropic. Codemagic, GitHub, Kobiton, Appetize and other names belong to their respective owners. This book is not affiliated with or endorsed by any of these companies.

---

## Contents

- Chapter 1 — Getting started
- Chapter 2 — iOS apps without a Mac: how it works
- Chapter 3 — The Apple Developer account
- Chapter 4 — Preparing the project
- Chapter 5 — Setting up Codemagic
- Chapter 6 — App Store Connect
- Chapter 7 — AdMob and your website
- Chapter 8 — Store listing and screenshots
- Chapter 9 — TestFlight and testing without an iPhone
- Chapter 10 — Submitting for review
- Chapter 11 — Handling rejections
- Chapter 12 — After launch
- Chapter 13 — Shipping updates
- Chapter 14 — Maintenance and security
- Chapter 15 — Troubleshooting (Q&A)
- Chapter 16 — Building and publishing apps on your own with Claude
- Appendix A — Complete checklist
- Appendix B — Glossary
- Appendix C — Template files

---

## Chapter 1 — Getting started

### Who this book is for

This book is for people who want to build iPhone/iPad apps and publish them on the App Store, but who don't have a Mac, only a Windows computer. That is the situation of many developers in Bangladesh, India and beyond. A Mac is expensive, and almost every guide online assumes there's a MacBook on your desk.

Everything written here was done by hand while publishing a real app:

- **ArchiveX File Manager**: an iPhone/iPad app for opening ZIP, RAR and 7Z files.
- All the work was done from a Windows computer, with no Mac and no iPhone.
- The app has AdMob ads and a $4.99 "Remove Ads" In-App Purchase.
- Apple blocked it the first time ("2.1 Information Needed"). After getting past that, the app is now live on the App Store.

So this book covers not only "what to do" but also "where you get stuck and how to get out". The boxes marked 💡 are that real experience.

### What you'll be able to do after reading this book

1. Build an iOS app in the cloud without a Mac (Codemagic, with GitHub Actions as an alternative).
2. Set up your Apple Developer account, certificates, profiles and API key correctly.
3. Set up the app, price, countries, privacy, age rating and In-App Purchase in App Store Connect.
4. Add AdMob ads, the consent message and app-ads.txt correctly.
5. Test the app on a real iPhone without owning one, and record the video Apple asks for.
6. Submit to App Review, handle rejections, publish, and ship later updates.
7. Know what needs renewing every year so your app doesn't suddenly disappear.

### What this book doesn't teach

Teaching Swift/SwiftUI programming is not the subject of this book. It assumes you already have your app's code or can write it.

Nobody can guarantee that an app will be approved. This book improves your chances and saves you time.

### Map of the whole journey

ArchiveX's real timeline shows how long each part takes:

| Day | What happened |
|---|---|
| Day 1 | Planning, checking library licenses, code, first successful build on Codemagic |
| Day 2 | Apple Developer portal, App Store Connect, IAP, AdMob, website, screenshots, TestFlight, submitted for review |
| Day 2, night | Apple's reply: "2.1 Information Needed": they want a video from a real device |
| Day 3 | Recorded the video on a real cloud iPhone without owning an iPhone, sent the reply |
| Day 4 | "Update Review" → submitted again |
| ~Day 12 | Approved, live on the App Store |

Allow about 2 weeks for the whole process the first time. From your second app on it is much faster, because most of the account, bank, tax and CI setup only has to be done once.

### Cost breakdown

| Item | Cost | Note |
|---|---|---|
| Apple Developer Program | $99 / year | The only mandatory cost |
| Codemagic | Free | 500 Mac minutes a month on a personal account (as of October 2026) |
| GitHub (private repo) | Free | |
| AdMob | Free | Google takes its share from your earnings |
| Website/domain | $0 if you already have one | Needed anyway for the privacy policy and app-ads.txt |
| Testing on a real iPhone | Free trial | Kobiton (Chapter 9) |
| Apple's commission | 15–30% of sales | 15% in the Small Business Program |

> 💡 **Lesson:** The biggest cost isn't money, it's waiting time: bank/tax verification, review, account recovery. Start anything that involves waiting first.

---

## Chapter 2 — iOS apps without a Mac: how it works

### The core problem

Apple's rules say you need Xcode to build an iOS app, and Xcode only runs on macOS. There is no Windows version.

The solution is to rent someone else's Mac. There are cloud services that take your code, build it on their Mac, and send it straight to App Store Connect. You never have to touch a Mac.

### Four routes

| Option | Cost | Advantages | Disadvantages |
|---|---|---|---|
| **Codemagic** ⭐ | 500 minutes a month free | Easy, creates certificates for you, uploads to the App Store | Free minutes are limited |
| GitHub Actions | ~200 free Mac minutes a month on private repos | Build where your code lives | Mac minutes count 10× |
| Xcode Cloud | 25 hours a month free | Apple's own | Needs Xcode on a Mac to switch it on the first time |
| Renting a cloud Mac | Paid by the hour/month | You get a whole Mac | Ongoing cost |

In this book Codemagic is the main route. A GitHub Actions template is also included as a backup, so work doesn't stop if Codemagic has a problem.

### Your working environment on Windows

- **Writing code:** VS Code or any editor. You get Swift syntax highlighting, but you can't run an iOS app on Windows.
- **Git + GitHub:** to store your code and connect it to Codemagic.
- **XcodeGen:** writing an Xcode project file (.xcodeproj) by hand is nearly impossible, because it's a complex file thousands of lines long. With XcodeGen you describe the whole project in a simple `project.yml` file. Codemagic generates the `.xcodeproj` from it during the build.

### How to "see" your app from Windows

| What you want to see | How |
|---|---|
| Whether the app runs, what the UI looks like | Appetize.io: an iOS simulator in your browser (upload Codemagic's simulator build) |
| How it runs on a real iPhone | Kobiton: a real iPhone in the cloud, controlled from your browser |
| App Store screenshots | Run the simulator on Codemagic and capture them automatically (Chapter 8) |
| On a friend's iPhone | Add them as a tester in TestFlight |

### The whole flow at a glance

```
Write code on Windows
   │ git push
   ▼
GitHub (private repo)
   │ Codemagic pulls the code
   ▼
Codemagic's Mac: xcodegen → xcodebuild → sign → IPA
   │ upload with the API key
   ▼
App Store Connect → TestFlight (testing) → App Review → App Store
```

---

## Chapter 3 — The Apple Developer account

### Individual or Organization?

| | Individual | Organization |
|---|---|---|
| Seller name on the App Store | Your own name | Your company's name |
| What you need | Apple Account, identity verification, card | All of the above + a D-U-N-S number (free, but can take a few weeks) and a company website |
| Fee | $99/year | $99/year |

For a first app, Individual is the fastest. ArchiveX was published from an Individual account. If you form a company later, the account can be converted to Organization.

### Before you open the account

1. You need an Apple Account (formerly Apple ID). Open it with an email you check all the time.
2. Two-Factor Authentication must be on.
3. You need a card that works for international payments (in Bangladesh usually a dual-currency card) to pay the $99.
4. Make your name and address match your government ID; they may be checked.

### ⚠ The biggest trap: your two-factor phone number

Whenever you sign in to App Store Connect from a new browser or a new computer, Apple sends a 6-digit code. If the code doesn't arrive you can't do anything: creating a new version, changing the Marketing URL, replying to the reviewer, everything is blocked.

> 💡 **Lesson (ArchiveX):** After the app was published, the browser's history and cookies were cleared, which signed us out everywhere. When we tried to sign in again, Apple said "we can't send a code to this number right now". When we asked to change the number, Apple said it would reply by email after 24 hours. For that whole time nothing could be done in App Store Connect.

**What to do:**

- Add two trusted phone numbers, ideally on two different carriers. (Apple Account → Sign-In and Security → Two-Factor Authentication → Trusted Phone Numbers)
- If you can, stay signed in with the same Apple Account on an old iPhone, iPad or Mac (a "trusted device"). When you sign in on a new browser, that device asks for permission by itself; tap Allow and it shows the 6-digit code. No SMS needed.
- When signing in, tap "Trust this browser".
- Don't clear cookies in the browser where you're signed in to App Store Connect.
- If the code doesn't arrive, don't keep pressing "Resend code". It only makes the block last longer.

### Note these down once the account is ready

| Information | Where to find it |
|---|---|
| Team ID (10 characters), membership renewal date, account email | developer.apple.com → Account → Membership details |

Keep membership auto-renew switched on. If you don't renew, all your apps are removed from the App Store.

---

## Chapter 4 — Preparing the project

### 1. Check the name

Two apps on the App Store can't have the same name. Check the name is free before you write any code:

- Search the App Store.
- The surest way: try the name when you create a New App in App Store Connect. If it's taken, it tells you right there.

> 💡 **Lesson:** The name "ArchiveX" had already been taken by someone else, so the App Store name became "ArchiveX File Manager". On the phone's home screen it still shows "ArchiveX", because that comes from `CFBundleDisplayName` in Info.plist. The App Store name and the home-screen name can be different.

### 2. Bundle ID

The Bundle ID is the app's permanent identity, for example `com.yourcompany.myapp`.

- It can't be changed after publishing.
- Use your domain name reversed (`yourcompany.com` → `com.yourcompany`).
- If you have a Share Extension or Widget, their Bundle IDs sit under the main ID, for example `com.yourcompany.myapp.share`.

### 3. project.yml (XcodeGen)

Start from the template `templates/01-project/project.yml`. It contains:

- The minimum iOS version, iPhone + iPad support
- `MARKETING_VERSION` (the version shown on the App Store) and `CURRENT_PROJECT_VERSION` (the build number)
- The Google Mobile Ads and UMP packages (Swift Package Manager)
- Google's test ad IDs in Debug, your real IDs in Release
- A safety script: if a test ID accidentally goes into an App Store build, the build itself fails

### Version and build numbers

| | MARKETING_VERSION | CURRENT_PROJECT_VERSION |
|---|---|---|
| Example | 1.0.0 → 1.0.1 → 1.1.0 | 1, 2, 3 … |
| When to change it | For every new App Store version, by hand | On every upload. The Codemagic template increases it automatically |

You can't upload the same build number twice. If an upload fails, check this first.

### 4. Info.plist

See `templates/01-project/Info.plist`. Important keys:

- `CFBundleDisplayName`: the home-screen name (it looks best under 12 characters).
- `GADApplicationIdentifier`: your AdMob App ID. Without it the app crashes on launch.
- `SKAdNetworkItems`: the list Google provides. Copy the current list from Google's quick-start page.
- If you ask for a permission you must give a reason. For example, if you use the camera, write clearly in English in `NSCameraUsageDescription` why you need it. Ask only for what you need. Unnecessary permissions are a common cause of rejection (5.1.1).

### 5. Privacy Manifest

Since 2024 Apple requires a `PrivacyInfo.xcprivacy` in every app. If you use certain APIs ("required reason APIs") you must write the code for why you use them:

| API | Common reason code | When you need it |
|---|---|---|
| UserDefaults | CA92.1 | Saving app settings (almost every app) |
| File timestamp | C617.1, 3B52.1 | Showing file dates |
| Disk space | E174.1, 85F4.1 | Checking there's space before writing files |

Template: `templates/01-project/PrivacyInfo.xcprivacy`. Google's SDKs bring their own manifests, so you don't have to write those separately.

### 6. App icon

- 1024 × 1024 PNG, with no transparency (alpha). Don't round the corners; Apple does that.
- Put it in `Assets.xcassets/AppIcon.appiconset`. Modern Xcode generates all the sizes from one 1024 image.
- An icon with a transparent background shows an error during upload.

### 7. Ads (AdMob) in code

- On first launch, show the UMP consent form, then call `MobileAds.shared.start()`.
- Show interstitials (full-screen ads) only at natural breaks, for example after a task finishes. Not right when the app opens, and not on every button.
- Put an "Ad Privacy Choices" button in Settings so users can change their consent.

### 8. In-App Purchase in code (StoreKit 2)

For a one-time purchase (non-consumable) like "Remove Ads":

- Never hard-code the price. Show `product.displayPrice`, so every country sees its own currency.
- To know whether it has been bought, check `Transaction.currentEntitlements`. Don't rely only on a local true/false.
- Listen to `Transaction.updates` from app launch, and call `finish()` on verified transactions.
- A "Restore Purchases" button is mandatory. Without it you'll be rejected (3.1.1).
- For local testing there's Xcode's `.storekit` file. Without a Mac, test with Sandbox in TestFlight (Chapter 9).

### 9. GitHub repo

- Create a private repo.
- Put these in `.gitignore`: `*.xcodeproj/`, `DerivedData/`, `.build/`, `xcuserdata/`. XcodeGen generates the `.xcodeproj` every time, so it doesn't need to be in the repo.
- Never put these in the repo: the `.p8` API key, certificates (`.p12`), any password.

---

## Chapter 5 — Setting up Codemagic

### Step 1: First, a GitHub account with your Gmail

If you don't have one:

1. github.com → Sign up.
2. Enter your Gmail address, a password and a username.
3. Verify your email with the code GitHub sends to your Gmail.

Your app's code will live in this GitHub account (the private repo from Chapter 4).

### Step 2: Then a Codemagic account through GitHub

1. Open codemagic.io and press the GitHub button on the login/sign-up page.
2. GitHub's page opens → press Authorize. Your Codemagic account is created; no separate password needed.
3. Later, use the same GitHub button to sign in.

> 💡 **Why GitHub?** If you sign up to Codemagic with just an email, it often asks for a company (business) email and may not accept a personal one like Gmail. Signing up with GitHub avoids this, and connecting your code is easier too. ArchiveX's Codemagic account was opened this way.

### Step 3: Add your app (repo)

1. On the Applications page, press **Add application** (top right) → Git provider: GitHub → Next: Authorize integration → Authorize Codemagic CI/CD.
2. Press **Install GitHub App**. On GitHub's page choose **Only select repositories** and give only the repo you need (not All repositories) → Install & Authorize.
3. Choose the repo and project type from the dropdown → Finish: Add application. We'll use our own `codemagic.yaml`.

### Step 4: App Store Connect API key

With an API key, Codemagic creates certificates, fetches profiles and uploads builds on your behalf, with no login or two-factor code.

1. App Store Connect → Users and Access → Integrations → App Store Connect API → Team Keys → **+**
2. Give it a name (for example "Codemagic"), Access: App Manager (or Admin).
3. Press Generate. Take three things:
   - **Issuer ID:** at the top of the page (looks like `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
   - **Key ID:** 10 characters
   - **.p8 file:** ⚠ it can only be downloaded once. Keep a backup somewhere safe.

> 💡 **Lesson:** Even when signing in to App Store Connect was blocked, Codemagic could still upload builds with this key. So keep the key safe, not just for Codemagic but as an emergency key too.

### Step 5: Give the key to Codemagic

Codemagic's left menu → Settings → Integrations (Team integrations for a team) → Developer Portal → Manage keys → Add key

- Give it a name (for example `app_store_key`); this is the name used in `codemagic.yaml`.
- Enter the Issuer ID, Key ID and the `.p8` file.

### Step 6: Create the App ID (developer.apple.com)

Certificates, Identifiers & Profiles → Identifiers → **+**

- App IDs → App → Bundle ID (Explicit): `com.yourcompany.myapp`
- Capabilities: tick only what your app uses (In-App Purchase is usually on already; App Groups, Push etc. if you need them).
- If you have a Share Extension, it needs its own App ID too.

### Step 7: Certificate and profile (from Codemagic itself)

Codemagic's left menu → Settings → codemagic.yaml settings → Code signing identities:

1. **iOS certificates** tab → in the form under "Generate a new code signing certificate", **Generate certificate**:
   - Reference name: for example `myapp_distribution`
   - Certificate type: Apple Distribution
   - App Store Connect API key: the key you added in the previous step
   - Then **Create certificate**.

   If you already have a certificate, you can bring it in from Apple with **Fetch certificate**.
2. **iOS provisioning profiles** tab → under "Get profiles from Apple Developer Portal", **Fetch profiles** (or create one yourself on developer.apple.com and upload the `.mobileprovision`). Type App Store, your app's Bundle ID, and the certificate from the previous step. Give it a reference name (for example `myapp_appstore`).
3. A Share Extension or Widget needs its own profile each.

To add or change files in Code signing identities you must be the team's Admin.

Remember: certificates and profiles last 1 year. When they expire, the live app keeps working, but you can't build a new update. Renewal is covered in Chapter 14.

### Step 8: codemagic.yaml

Put `templates/02-ci/codemagic.yaml` in the root of your repo, then change:

- `MyApp` → your project/scheme name
- `app_store_key`, `myapp_distribution`, `myapp_appstore` → the names you gave in Codemagic
- `APP_STORE_APPLE_ID` → the Apple ID you get after creating the app in App Store Connect (Chapter 6)

The template has three workflows:

| Workflow | What it does | When to run it |
|---|---|---|
| ios-check | Build without signing, to see if there are errors | After every big change |
| ios-simulator | A simulator build to run on Appetize | When you want to see the UI |
| ios-release | Signed IPA → App Store Connect | At release time |

### Step 9: Run it

Codemagic → your app → Start new build → branch `main` → choose the workflow → Start.

- At the end you'll find the log and the IPA under Artifacts.
- If `ios-release` succeeds, the build shows up in App Store Connect's TestFlight tab 10–30 minutes later.

### Tips to save minutes

- Switch off automatic builds on every push. Run them by hand only.
- Run `ios-check` (cheap) first, and `ios-release` only when it succeeds.
- Set a `max_build_duration` limit so a stuck build doesn't eat your minutes.

### When a build fails: common causes

| Error message (partial) | Cause | Fix |
|---|---|---|
| No profiles for 'com…' were found | The profile's Bundle ID doesn't match, or the profile wasn't fetched | Correct profile in Code signing identities, correct reference name in the yaml |
| doesn't include signing certificate | The profile was made with a different certificate | Re-create the profile with the new certificate |
| The bundle version must be higher | Build number is the same as last time | Use the template's automatic build number |
| Missing required icon / alpha channel | Problem with the icon | 1024×1024, no transparency |
| Crash mentioning GADApplicationIdentifier | No AdMob App ID in Info.plist | See the Info.plist template |

---

## Chapter 6 — App Store Connect

### Step 1: Business paperwork (do this first)

App Store Connect → Business (formerly "Agreements, Tax, and Banking")

1. Accept the **Paid Apps Agreement**. It's mandatory if you have In-App Purchases, even in a free app.
2. Add a **Bank Account** (account name, number, SWIFT/routing details, whatever your bank requires).
3. **Tax Forms:** W-8BEN as an individual outside the United States. Read the questions carefully. If you're unsure about tax decisions, talk to a professional.
4. Wait until everything shows "Active".

> 💡 **Lesson:** If the Paid Apps Agreement isn't active, In-App Purchases don't load even in TestFlight. The product list comes back empty, and it looks like a bug in your code. Get this done first.

**Small Business Program:** if you earn less than $1 million a year, you can apply to cut Apple's commission from 30% to 15% (developer.apple.com → App Store Small Business Program).

### Step 2: Create the new app

Apps → **+** → New App

| Field | What to enter |
|---|---|
| Platforms | iOS |
| Name | The App Store name (30 characters) |
| Primary Language | English (U.S.) or whatever you want |
| Bundle ID | Your App ID from the dropdown |
| SKU | A code for yourself, e.g. `myapp-ios` (nobody else sees it) |
| User Access | Full Access |

After creating it, the App Information page shows an **Apple ID** (10 digits). Put it in `APP_STORE_APPLE_ID` in `codemagic.yaml`.

### Step 3: App Information

- **Category:** a primary and an optional secondary category.
- **Content Rights:** whether there is third-party content.
- **Age Rating:** fill in the questionnaire. A normal utility app is usually 4+, even with ads.
- **Privacy Policy URL:** the page on your website (Chapter 7).

### Step 4: Pricing and Availability

- **Price:** Free (or your price).
- **Availability:** which countries.
- **Encryption and France:** if your app has encryption such as AES (for example password-protected files), App Store Connect asks some questions. Distribution in France needs a separate declaration (ANSSI).

> 💡 **Lesson:** ArchiveX has AES encryption. Because the French declaration is a hassle, France was left out and the app was published in the other 174 countries. France can be added later with the declaration.

If your app only uses HTTPS and has no encryption of its own, setting `ITSAppUsesNonExemptEncryption = NO` in Info.plist saves you answering the question every time. If you're not sure, answer the questionnaire in App Store Connect.

### Step 5: App Privacy

App Privacy → Get Started. You must declare all data the app and its SDKs collect. With AdMob you must answer "Yes, we collect data". Sample answers: `templates/04-app-store/app-privacy-admob.md`.

Don't forget to press **Publish** at the end.

### Step 6: Create the In-App Purchase

Monetization → In-App Purchases → **+**

| Field | Example |
|---|---|
| Type | Non-Consumable (one-time, permanent) |
| Reference Name | Remove Ads (only for you) |
| Product ID | `com.yourcompany.myapp.removeads`. Must match the code exactly; can't be changed later |
| Price | Choose from the price tiers, e.g. $4.99 |
| Display Name / Description | What users see: "Remove Ads" / "Remove all ads permanently. One-time purchase." |
| Review Screenshot | A screenshot of the purchase screen in the app (Chapter 8) |

When everything is filled in, the status becomes "Ready to Submit". The first IAP has to be submitted together with an app version (Chapter 10).

---

## Chapter 7 — AdMob and your website

### Step 1: Add the app to AdMob

1. admob.google.com → Apps → Add app → iOS.
2. To "Is the app listed on a supported app store?" answer **No** the first time. The app isn't published yet.
3. Enter the app's name. You'll get an App ID: `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY`.
4. Ad units → Add ad unit: Banner and Interstitial. Each has an ID: `ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ`.
5. Put these real IDs in the Release section of `project.yml`. Debug keeps Google's test IDs.

> ⚠ Never click the real ads in your own app, not even while testing. Your AdMob account could be closed. That's why Debug builds use test IDs.

### Step 2: Consent message (GDPR and US states)

AdMob → Privacy & messaging

1. **European regulations (GDPR):** create a new message, choose the app, enter the privacy policy URL. Keep the "Do not consent" button. Then Publish.
2. **US state regulations:** create one the same way and Publish.
3. The UMP SDK in your app's code shows these messages by itself, wherever the law requires.

### Step 3: Three things on your website

| Page | Example address | Template |
|---|---|---|
| Privacy Policy | https://yourdomain.com/myapp/privacy | `templates/03-website/privacy-policy.html` |
| Support | https://yourdomain.com/myapp/support | `templates/03-website/support.html` |
| app-ads.txt | https://yourdomain.com/app-ads.txt (at the root of the domain) | `templates/03-website/app-ads.txt` |

In the app-ads.txt line, replace `pub-XXXXXXXXXXXXXXXX` with your AdMob Publisher ID (AdMob → Settings → Account information). The final `f08c47fec0942fa0` is the same for every AdMob user.

Open the addresses in a browser and make sure each page opens properly and app-ads.txt shows as plain text.

### ⚠ Marketing URL: the mistake everyone makes

AdMob looks for app-ads.txt on the domain of the **Marketing URL** in your App Store listing. It does not look at the Support URL or the Privacy URL.

> 💡 **Lesson (ArchiveX):** The first version only had a Support URL; the Marketing URL was empty. After the app went live, AdMob showed "We couldn't verify ArchiveX File Manager", even though the app-ads.txt file was completely correct. And the Marketing URL can only be changed when you submit a new version, so an update had to be shipped just for this.

**What to do:** before submitting the first version, set Marketing URL = `https://yourdomain.com`, just the domain.

### Step 4: In AdMob after the app is live

1. Apps → View all apps → in the app's row, "Stores" column: **Add store** (or app → App settings → App stores → Add store) → find the app on the App Store and link it. A freshly published app can take 24–48 hours, sometimes a week, to show up in search.
2. AdMob reviews the app (app readiness review, can take a few days).
3. Apps → View all apps → app-ads.txt → open the app's row and press **Check for updates**. Verification can take up to 24 hours.

On the same page, "How to set up app-ads.txt" shows the full line with your Publisher ID, ready to copy.

---

## Chapter 8 — Store listing and screenshots

### The text

`templates/04-app-store/store-listing.md` has every field, character limit and rule. The key points:

- The first 2–3 lines matter most; that's all people see before tapping "more".
- **Keywords:** 100 characters, separated by commas, no spaces after commas. Don't repeat words from the name or subtitle.
- ❌ Don't claim "best", "#1", "fastest", "unlimited", other brands' names, or features the app doesn't have. These are reasons for rejection (2.3).
- **Promotional Text** can be changed at any time without review. Useful for announcing offers or news.

### Screenshot sizes

| Device | Size (portrait, pixels) | When you need it |
|---|---|---|
| iPhone 6.9" | 1320 × 2868 | iPhone apps (main size) |
| iPhone 6.5" | 1242 × 2688 | Older size, good to include |
| iPad 13" | 2064 × 2752 | Mandatory if you support iPad |

1 to 10 screenshots per size.

### Screenshots without a Mac: the automatic method

You can run the simulator on Codemagic's Mac and capture screenshots. This is how it was done for ArchiveX:

1. **A "screenshot mode" in the app:** when the app receives a launch argument (for example `-Screenshot home`) it opens that screen directly, shows nice sample data and hides ads. This code only exists in Debug builds.
2. **In the Codemagic workflow:**
   - Create and boot a simulator: `xcrun simctl create`, `xcrun simctl boot`
   - Tidy the status bar: `xcrun simctl status_bar <id> override --time "9:41" --batteryLevel 100 …`
   - Install the app and launch it on each screen: `xcrun simctl launch <id> com.yourcompany.myapp -Screenshot home`
   - Take the picture: `xcrun simctl io <id> screenshot home.png`
3. Running it on the iPhone Pro Max and iPad Pro 13-inch simulators gives the right sizes automatically.

> 💡 **Lesson:** When a new simulator boots for the first time, some system messages pop up. Launch the app once and wait a minute before taking screenshots, or the messages end up in the pictures.

**Easy alternative:** run the app on Appetize.io, take screenshots, and lay them out at the right size in Canva/Figma.

### The IAP review screenshot

An In-App Purchase needs a screenshot of the purchase screen in the app. It isn't shown on the App Store; only the reviewer sees it. Use the same screenshot mode to capture the "Settings/Remove Ads" screen.

---

## Chapter 9 — TestFlight and testing without an iPhone

### TestFlight

1. When `ios-release` succeeds, the build arrives in App Store Connect → TestFlight. It shows "Processing" first; this takes 10–30 minutes.
2. If the encryption question appears ("Missing Compliance"), answer it.
3. Internal Testing → **+**: create a group and add yourself (and your team). Internal testers don't need Apple's review to get a build.
4. If you want to give it to outside people (External Testing), the first build goes through a short Beta review.
5. Anyone with an iPhone installs it through the TestFlight app.

### Testing In-App Purchases (Sandbox)

Purchases in a TestFlight build happen in Sandbox; no real money is charged.

- **Conditions:** the Paid Apps Agreement is active (Chapter 6) and the IAP details are complete.
- **Test:** buy → ads disappear → delete the app and reinstall → Restore Purchases → ads disappear again.

### If you don't have your own iPhone

| Service | What it is | Cost | What it's good for |
|---|---|---|---|
| Appetize.io | iOS simulator in the browser | A few free minutes a month | Seeing the UI and main features; upload Codemagic's `ios-simulator` zip |
| Kobiton | A real iPhone in the cloud | Some minutes on the free trial (we got 300 minutes) | Testing on a real device and the App Review video (Chapter 11) |
| A friend's iPhone + TestFlight | A real phone | Free | The most realistic test |

### Test these before publishing

- ☐ No crash on first launch; the consent form appears properly
- ☐ Every main feature works from start to finish
- ☐ No button is "coming soon" or does nothing
- ☐ Banner ads show; interstitials only at natural breaks
- ☐ Buying Remove Ads and Restore both work
- ☐ The layout is right on iPad (if you support iPad)
- ☐ The app doesn't crash without internet
- ☐ Text is readable in Dark Mode

---

## Chapter 10 — Submitting for review

### Step by step

App Store Connect → your app → iOS App → 1.0 Prepare for Submission

1. Upload the screenshots (Chapter 8).
2. Promotional Text, Description, Keywords, Support URL, **Marketing URL** (don't forget it!).
3. In the Build section, **+** → choose the TestFlight build.
4. In In-App Purchases and Subscriptions, **+** → choose Remove Ads. The first IAP must go with the first version.
5. **App Review Information:**
   - **Sign-in required:** untick it if there's no login. If there is, give a working demo account.
   - **Contact:** name, phone, email.
   - **Notes:** what the app is, how to test it, which outside services it uses. Template: `templates/04-app-store/app-review-notes.txt`. If needed, give a link to sample files.
6. **Version Release:**
   - *Manually release:* when approved, you press Release yourself (safest the first time).
   - *Automatically release:* live as soon as it's approved.
7. At the top: Add for Review → Submit to App Review.

The status goes "Waiting for Review" → "In Review" → "Pending Developer Release"/"Ready for Distribution" (or a rejection).

### How long it takes

Usually 24–48 hours. A new account's first app is more likely to get questions, so allow a few more days.

---

## Chapter 11 — Handling rejections

### Common reasons for rejection

| Guideline | Meaning | Usual fix |
|---|---|---|
| 2.1 App Completeness / Information Needed | The app crashes, something doesn't work, or Apple wants more information | Fix the crash; give the information and video they ask for |
| 2.3 Accurate Metadata | Description/screenshots don't match the app, or exaggerate | Make the text and images match the app |
| 3.1.1 In-App Purchase | Selling digital things without IAP, no Restore button | Use IAP, add a Restore button |
| 4.3 Spam | A template app or nearly identical to others | Add your own real value to the app |
| 5.1.1 Data Collection | Unneeded permissions, missing or incomplete privacy policy | Only needed permissions, a clear privacy policy |

### "2.1 Information Needed": almost certain on a new account

On a new developer account Apple often sends questions about the first app. Usually they want:

1. A screen recording of the app running on a real device, starting by opening the app from the Home Screen
2. The app's purpose and target users
3. How to reach the setup and main features
4. Outside services (ads, analytics, login)
5. Differences between countries
6. Regulated industries or third-party content
7. Details of the In-App Purchase

This is not a rejection; it's a request for information. If you answer properly, the app is usually approved.

### A video on a real iPhone without owning one (Kobiton)

> 💡 For ArchiveX, Apple wanted a video from a real device, but there was no iPhone. The video was recorded on a real cloud iPhone 16e (iOS 27) through Kobiton and sent in, and the app was approved.

**1. A separate build for the video.** Make a special build that:

- Uses Google's test ads: showing or tapping your own real ads on a remote phone is against AdMob's rules.
- Has sample data preloaded (if needed): no hassle getting files onto a remote phone, and the whole flow fits in one video.
- Is otherwise exactly the same as the submitted build.

In Codemagic, make a copy of the `ios-release` workflow, pass the test ad IDs in `--archive-xcargs`, and remove the publishing section. Download the IPA from Artifacts.

**2. Kobiton**

1. Open a free account at kobiton.com.
2. Upload the IPA under Apps.
3. Choose a real iPhone on the newest iOS and start a manual session. The app installs on the phone.
4. Minutes are limited, so write down on paper beforehand what you'll show and in what order.

**3. What to show in the video**

1. Starting the app by tapping its icon on the phone's Home Screen.
2. The main tasks one by one, from start to finish.
3. The In-App Purchase screen and the Restore Purchases button.
4. Login/account deletion, if the app has it. If not, say so in your reply.

**4. Downloading and preparing the video**

- When the session ends, download the video from that session's Overview page.
- On a remote phone there's a wait after every tap. Cut only the empty waiting parts, nothing else.
- Give it a clear name, for example `MyApp-review-iPhone16e-iOS27.mp4`.

### What didn't work for us

| Service | Problem |
|---|---|
| Firebase Test Lab | No video on phones with the newest iOS |
| BrowserStack / TestingBot (trial) | Phones busy, or only older iOS |
| AWS Device Farm | The SMS code for opening the account never arrived |
| Appetize.io | A simulator, not a real phone. Not accepted for Apple's video |

### Sending the reply

1. App Store Connect → App Review → Apple's message → Reply.
2. Template: `templates/04-app-store/review-reply-2.1.txt`. Answer each of Apple's questions in the same order. Attach the video.
3. Be honest: say which phone and iOS it was recorded on, what's different in the video build (test ads, sample files), and that only waiting time was cut.
4. Put the same information in App Review Information → Notes as well.

### Resubmitting: an odd step

> 💡 **Lesson:** Right after sending the reply, trying to "Resubmit" may show "Version is not ready". The next day an "Update Review" button appears on the version page. Press it, and then "Resubmit to App Review" becomes available. Be patient; don't keep submitting again.

### What not to do

- Don't reply angrily or argue.
- Don't write long texts about things they didn't ask for.
- If you disagree, explain calmly. If it really is a misunderstanding, you can appeal to the App Review Board.

---

## Chapter 12 — After launch

### Day one

1. If you chose manual release, press **Release This Version**. It can take a few hours to show up on the App Store.
2. Open the app's page on the App Store and check: name, screenshots, price, IAP, and the Developer Website link at the bottom (it shows if you set a Marketing URL).
3. AdMob: link the App Store listing, then app-ads.txt → Check for updates (Chapter 7).
4. Download it from the App Store yourself (or on a friend's phone) and check that real ads appear. Don't click them.

### What to watch regularly

| What | Where |
|---|---|
| Crashes | App Store Connect → TestFlight/Analytics, Xcode Organizer (if you have a Mac) |
| Downloads, sales | App Store Connect → Analytics, Sales and Trends |
| Reviews and ratings | App Store Connect → Ratings and Reviews. Reply politely, and say when a problem is fixed |
| Ad earnings | AdMob → Home/Reports |

### How the money arrives

- **Apple:** pays each month's sales to your bank roughly at the end of the following month, if you pass your country's minimum. Details: App Store Connect → Payments and Financial Reports.
- **AdMob:** pays the next month once your earnings pass a set threshold (usually $100). Fill in your payment details and tax forms in AdMob → Payments beforehand.

---

## Chapter 13 — Shipping updates

### Steps for every update

1. Change the code. Raise `MARKETING_VERSION` in `project.yml`: 1.0.0 → 1.0.1 for small fixes, 1.0.1 → 1.1.0 for new features.
2. Push to GitHub.
3. Codemagic: `ios-check` first, then `ios-release` if it succeeds.
4. App Store Connect → your app → **+** next to iOS App → new version (for example 1.0.1).
5. Write "What's New in This Version".
6. Choose the build → Add for Review → Submit.

Update reviews are usually faster than the first one.

### What can be changed when

| Item | When it can be changed |
|---|---|
| Promotional Text | Any time, without review |
| Description, Keywords, screenshots | With a new version |
| Marketing URL, Support URL | With a new version |
| App name, Subtitle | With a new version |
| Price, countries | Any time (Pricing and Availability) |
| Bundle ID, IAP Product ID | Never |

### Phased Release

For big changes you can turn on **Phased Release for Automatic Updates**. The update reaches everyone gradually over 7 days, and you can pause it midway if problems appear.

---

## Chapter 14 — Maintenance and security

### Yearly tasks

| What | When | If you don't |
|---|---|---|
| Apple Developer membership ($99) | Every year (keep auto-renew on) | All your apps are removed from the App Store |
| Distribution certificate + profile | Every year, before they expire | The live app keeps working, but you can't build new updates |
| Building with the new Xcode/iOS SDK | Apple makes a new SDK mandatory every year (usually in spring) | Builds with the old SDK aren't accepted |
| Google Mobile Ads SDK update | 1–2 times a year | Earnings drop on old SDKs, and eventually stop |
| Agreements / tax forms | When Apple issues new terms | Payments and IAP may stop |
| App Privacy, Privacy Policy | When you add a new SDK or feature | Rejection |

> 💡 Put the expiry dates in your calendar with a reminder one month ahead.

### Renewing the certificate (Codemagic)

1. Codemagic → Settings → codemagic.yaml settings → Code signing identities → iOS certificates → Generate certificate (Certificate type: Apple Distribution, the same API key → Create certificate).
2. Fetch/create the provisioning profile again with the new certificate.
3. If you keep the same reference names, you don't have to change `codemagic.yaml`.
4. Run `ios-release` once to check.
5. Apple allows only a few Distribution certificates per account. If there's no room, delete an unused old one on developer.apple.com. Don't delete the one your builds use.

### Account security

- Two trusted phone numbers and, if possible, a trusted Apple device (Chapter 3).
- Don't clear cookies in the browser where you're signed in to App Store Connect.
- Don't use your Apple Account password anywhere else.
- When adding team members, give them only the role they need in Users and Access. Never share your own login.

### Backups: keep things in three places

| What | Where |
|---|---|
| Source code | GitHub (private) + a clone on your own computer |
| `.p8` API key | A password manager or encrypted drive. Never on GitHub |
| Website pages (privacy, support, app-ads.txt) | The website's repo + a local copy |
| Important details (Team ID, Apple ID, AdMob IDs, expiry dates) | A notes file |

---

## Chapter 15 — Troubleshooting (Q&A)

**Q: The build succeeded on Codemagic, but it doesn't show up in TestFlight.**
A: Wait 10–30 minutes. If it still doesn't appear, check your email from Apple. It often reports a problem with the icon, Info.plist or the privacy manifest.

**Q: The IAP price doesn't load in TestFlight; the product list is empty.**
A: Check that the Paid Apps Agreement, bank and tax are "Active". Check that every IAP field (including the review screenshot) is filled in and that the Product ID matches the code exactly.

**Q: AdMob says "We couldn't verify… app-ads.txt".**
A: (1) Check that the App Store listing has a Marketing URL; if not, add it in a new version. (2) Check that https://yourdomain.com/app-ads.txt opens in a browser. (3) Check that the Publisher ID matches. (4) Wait 24 hours and press "Check for updates".

**Q: The two-factor code isn't arriving.**
A: Don't keep pressing Resend. If you have a trusted Apple device, get the code there. If not, try once more after a few hours. Account recovery is the last resort and can take days. Prevention: two trusted numbers.

**Q: It says "Version is not ready" and won't resubmit.**
A: After replying to Apple's message, wait until the next day. When the "Update Review" button appears on the version page, press it, then "Resubmit to App Review".

**Q: The app crashes on launch (only in the Release build).**
A: The most common cause is a missing or wrong `GADApplicationIdentifier`. Check Info.plist and the Release section of `project.yml`.

**Q: The name I want is taken.**
A: Add a description of what it does ("MyApp – PDF Scanner"). You can keep the home-screen name (`CFBundleDisplayName`) short.

**Q: My free Codemagic minutes are used up.**
A: Wait until next month, or use the GitHub Actions template (`templates/02-ci/github-actions/ios-release.yml`).

**Q: Ads aren't showing (in the live app).**
A: For a new app, ads are limited until AdMob's review is finished. Check that you linked the App Store listing and published the consent messages. In Europe, fewer ads show when users don't consent; that's normal.

**Q: What should I answer to the export compliance questions?**
A: If you only use HTTPS, you're usually exempt. If you do your own encryption (for example locking files with AES), read the questions carefully. Distribution in France needs a separate declaration. If you're not sure, you can start without France.

---

## Chapter 16 — Building and publishing apps on your own with Claude

No Mac, and you don't know Swift? The AI assistant Claude Desktop (the Code tab) can write the code for you, run the builds, and fill in most forms in the browser. This book's example app was published this way too.

Below are sample prompts, step by step, for a simple tasbih (dhikr) counter app. For your own app, change the features part, and fill in your own details where you see [ ] brackets.

### Remember before you start

- **One project, one folder, one session.** In Claude Desktop's Code tab, open a new folder (for example `Desktop\MyApp`) and give every prompt there. If you take a break, come back to the same session.
- **One prompt per step.** Only give the next one when the previous step has succeeded.
- **Some tasks only you can do:** opening accounts, entering passwords or cards, two-factor codes, accepting agreements, paying. Claude doesn't do these, by its safety rules. Every step lists them separately under "👤 Your part".
- Claude asks for your permission before publishing, submitting or pushing. Understand what it's doing, then say "yes".
- **Browser work:** once you sign in to Claude Desktop's built-in browser, Claude can fill in the forms itself.

### Step 0 — Preparation (👤 all your part)

1. Open a GitHub account with your Gmail.
2. Open a Codemagic account through GitHub (codemagic.io → GitHub button).
3. Join the Apple Developer Program ($99/year). Add two phone numbers for two-factor authentication.
4. Open an AdMob account (if you want to show ads).
5. Your own domain is best. If you don't have one, GitHub Pages will do.

### Step 1 — Planning (no code)

```
You are a senior iOS developer and App Store release expert. I have no Mac or iPhone,
only a Windows computer. I want to build a real iOS app that can be published on the App Store.

App: a simple tasbih (dhikr) counter, for iPhone and iPad.

First ask me: what the app should be called, and what the Bundle ID should be.
Don't choose them yourself until I answer.

Features:
- Tapping a big button increases the count, with a light vibration (haptic)
- A few dhikr come preset (e.g. SubhanAllah 33, Alhamdulillah 33, Allahu Akbar 34),
  and users can add their own
- It tells you when a target is reached
- Totals for today and previous days
- Dark mode, Bangla and English
- No internet, account or permissions needed

Revenue: an AdMob banner, interstitials only at natural breaks, and a one-time,
permanent "Remove Ads" In-App Purchase (StoreKit 2).

Rules:
- Swift, SwiftUI, XcodeGen (project.yml). Builds run on Codemagic, because I have no Mac
- No fake features, fake buttons or fake purchases
- If you use a library, check its license
- Follow the App Store rules, especially 4.3 spam: include something that sets it
  apart from other counter apps

Don't write code yet. First show me:
1) feasibility and what I'll need
2) the folder structure
3) cost and time estimates
4) all the steps of the work
Only start when I approve.
```

👤 **Your part:** read the plan. If you want changes, say so, then write "start".

### Step 2 — Project and code

```
The plan is approved. Now build the whole app:
- project.yml (XcodeGen), all Swift files, Info.plist, PrivacyInfo.xcprivacy,
  app icon (1024×1024, no transparency)
- Google's test ad IDs in the Debug build, placeholders in the Release build.
  I'll give the real IDs later. If a Release build accidentally uses test IDs,
  the build must fail
- UMP consent before showing ads; Remove Ads, Restore Purchases and
  Ad Privacy Choices in Settings
- Bundle ID: com.[your name or company].[short app name]
- Take AdMob's SKAdNetworkItems list from Google's current documentation page and
  put it in Info.plist; don't make one up
- If you need Python to make the icon, first check whether my computer has it;
  if not, tell me what to do
- Put a README in Bangla in a docs folder: what was built, and how to change it later
- Don't put my passwords, keys or personal details in any file
At the end, tell me which files were created and what hasn't been checked yet.
```

### Step 3 — Putting the code on GitHub

```
Make this folder a git repo, add a .gitignore (xcodeproj, DerivedData, .p8, .p12
must never go in), and make the first commit.

Then open github.com in the built-in browser. Once I sign in, create a **private**
repo (name: [repo name]). Then ask for permission to push the code, and push when
I say "yes".

If the push fails, find the reason and tell me ("Repository not found" usually means
the repo wasn't created, or the name or account is different).
At the end, tell me what I need to do on GitHub for Codemagic.
```

👤 **Your part:** sign in to GitHub in the built-in browser. When Claude asks permission to push, understand it and say "yes". This is safer than creating the repo yourself, because there's less risk of mixing up the name or account.

**Letting Codemagic see the repo:** every new repo has to be added to the Codemagic GitHub App's permissions, otherwise Codemagic can't see it. GitHub → Settings → Applications → Codemagic → Configure → choose the new repo under Repository access (or ask Claude to do it in the browser).

### Step 4 — The first build on Codemagic

```
Write an ios-check workflow in codemagic.yaml: generate the project with XcodeGen,
then build without signing. Give me the command to push.

Then open Codemagic in the built-in browser. Once I sign in, add the app and run ios-check.

Steps to add the app: Add application → Select team → Personal account →
Next: Connect repository → GitHub → Next: Select repository → choose the repo,
project type **iOS** → Finish: Add application.
Then "Finish build setup" appears next to the app; from there, "Start your first build".

If the build fails, read the log, fix the error, ask me to push again, and run it again.
Keep going until it succeeds.
Tell me each time how many minutes were used.
```

👤 **Your part:** sign in to Codemagic. Run the push command when Claude tells you to.

### Step 5 — Seeing it, and screenshots

```
1) Make an ios-simulator workflow that gives me a zip I can run on Appetize.io.
2) Make an ios-screenshots workflow. Add a "screenshot mode" to the app that only
   works in Debug builds, and take 5 screenshots each at iPhone 6.9", iPhone 6.5"
   and iPad 13" sizes. No ads in the screenshots.
3) In-App Purchase products don't load in the simulator, so add a StoreKit
   configuration file to the Debug screenshot mode, so the "Remove Ads" row in
   Settings shows a price (not grey or empty).
At the end, tell me where to download the artifacts from.
```

The screenshot step takes about 12 minutes and the whole thing about 15; be patient. While the build runs there's no need to download files or send new prompts.

👤 **Your part:** download the screenshot zip from Artifacts on the Codemagic build page. Opening that link directly asks for a login, so download it from the browser where you're signed in to Codemagic. (If you ask Claude to download it, it will ask your permission.) Look at the pictures yourself. Then open a free Appetize.io account, upload the zip and try the app yourself. If you notice any problem, tell Claude.

### Step 6 — Website pages

```
Make these for my app:
- Privacy Policy (describe the ads and the In-App Purchase truthfully)
- Support page
- app-ads.txt
My domain: [yourdomain.com, or write "no domain, use GitHub Pages"]
Tell me step by step how to publish them. Then open them in the browser and check
they all open properly.
Remember, app-ads.txt has to be at the root of the domain.
```

### Step 7 — AdMob

👤 **Your part first:** add the app in AdMob (Apps → Add app → iOS → No). Create two ad units, Banner and Interstitial, and take their IDs.

```
My AdMob IDs:
App ID: [ca-app-pub-...~...]
Banner: [ca-app-pub-.../...]
Interstitial: [ca-app-pub-.../...]
Publisher ID: [pub-...]
Put these only in the Release build, and update app-ads.txt.
Then open AdMob in the built-in browser; I'll sign in. In Privacy & messaging,
create two consent messages, European regulations and US state regulations.
Show me before publishing.
```

### Step 8 — Apple setup

👤 **Your part first:**

1. App Store Connect → Users and Access → Integrations → App Store Connect API → Team Keys → **+** → Access: App Manager → download the `.p8` file and keep it safe.
2. In Business, complete the Paid Apps Agreement, bank and W-8BEN.

```
I've created the API key. Here are the Key ID and Issuer ID: [Key ID], [Issuer ID].
The .p8 file is at [file location].
Now, once I sign in to the built-in browser, do these:
1) Add the key in Codemagic
2) Create the App ID on developer.apple.com, with In-App Purchase on
3) Create the Apple Distribution certificate and App Store profile in Codemagic
4) Create the new app in App Store Connect. If the name isn't free, suggest alternatives
5) Create the Remove Ads In-App Purchase (Non-Consumable, $[price])
After each step, tell me what happened. Never show the contents of the .p8 file in the
chat or put it in git.
```

👤 **Your part:** sign in to App Store Connect, developer.apple.com and Codemagic, and enter the two-factor codes. If an agreement needs accepting, do it yourself.

### Step 9 — Store listing and App Privacy

```
Write these for my app:
- Name (30 characters), subtitle (30), promotional text, description, keywords (100 characters)
- App Review Notes
- App Privacy answers (based on Google's current list for AdMob)
- Age rating answers
Don't claim "best", "#1", or anything the app doesn't have.
Then put them into App Store Connect, upload the screenshots, and put my domain in
the Marketing URL.
Show me before saving. Don't submit.
```

### Step 10 — Release build and TestFlight

```
Add an ios-release workflow to codemagic.yaml. The build number should increase by
itself, and the build should upload to App Store Connect. Ask me to push, then run it.
Watch until the build reaches TestFlight, and answer the encryption question if it appears.
Add me as an internal tester.
```

### Step 11 — Testing on a real iPhone, and the video

```
I don't have an iPhone. Apple may ask for a video of the app running on a real device.
Make a separate build with test ads. Tell me the steps to run it on a real iPhone on
Kobiton, and give me a list, in order, of what to show in the video:
starting from launching the app, then the main features, Remove Ads and Restore.
```

👤 **Your part:** open a free Kobiton account, upload the IPA, and record the video following the list.

### Step 12 — Submitting for review

```
Before submitting, go through the checklist:
build attached, IAP attached, Marketing URL, Privacy URL, screenshots,
App Privacy Published, Review Notes.
Tell me if anything is missing. If everything is right, ask my permission before
"Submit for Review".
```

### Step 13 — If Apple asks questions or rejects the app

```
Apple sent this message: [paste the whole message]
Explain which guideline it's about. Tell me what needs fixing, and write a polite,
specific reply in English.
If the code needs changing, change it and make a new build. Show me before sending.
```

### Step 14 — After launch

```
The app is live. Now:
1) Link the App Store listing in AdMob and verify app-ads.txt
2) Check that the Developer Website link shows on the App Store page
3) Keep a note in the docs folder: all the IDs, expiry dates (certificate, membership),
   and how to ship the next update
4) Check that the code backup is in order
```

### Step 15 — Shipping updates later

```
[Write what you want to change]. Raise the version number, build it, create a new
version in App Store Connect, and write "What's New".
Ask my permission before submitting.
```

### Working tips

- **Ask for verification:** at the end of every step, write "Tell me separately what you didn't verify."
- **When stuck:** add a screenshot and write "Look at this, where's the problem?"
- **To save minutes:** "Run ios-check first, and ios-release only if it succeeds."
- **To keep notes:** now and then write "Write down what's been done so far in docs." The next session can pick up from that note.

> ⚠ AI can make mistakes. Check the result of every step yourself, especially before money, agreements and submissions. The chapters of this book are your guide for that checking.

---

## Appendix A — Complete checklist

### Account and business

- ☐ Apple Developer membership active, auto-renew on
- ☐ Two trusted phone numbers
- ☐ Paid Apps Agreement, bank, W-8BEN all "Active"
- ☐ (Optional) Small Business Program

### Project

- ☐ Checked the name is free
- ☐ Bundle ID final
- ☐ `project.yml`: version, Team ID, real AdMob IDs in Release
- ☐ `Info.plist`: Display Name, GADApplicationIdentifier, SKAdNetworkItems
- ☐ `PrivacyInfo.xcprivacy`
- ☐ 1024×1024 icon, no transparency
- ☐ Restore Purchases button
- ☐ Private GitHub repo, no secret files

### Codemagic

- ☐ GitHub connected
- ☐ API key (`.p8` kept safe)
- ☐ App ID, Distribution certificate, App Store profile
- ☐ `codemagic.yaml`, `ios-check` succeeds

### App Store Connect

- ☐ New app, Apple ID put in the yaml
- ☐ Category, Age Rating, Privacy Policy URL
- ☐ Price and countries (France, if you use encryption)
- ☐ App Privacy Published
- ☐ IAP "Ready to Submit" + review screenshot

### AdMob and website

- ☐ AdMob app + ad units
- ☐ GDPR + US states consent messages Published
- ☐ Privacy Policy and Support pages live
- ☐ app-ads.txt at the root of the domain

### Submission

- ☐ `ios-release` succeeds, tested in TestFlight
- ☐ Screenshots (iPhone + iPad)
- ☐ Description, Keywords, Support URL, Marketing URL
- ☐ Build + IAP attached
- ☐ App Review Notes
- ☐ Submit

### After launch

- ☐ Release
- ☐ App Store link in AdMob
- ☐ app-ads.txt verified
- ☐ Expiry dates in your calendar

---

## Appendix B — Glossary

| Term | Meaning |
|---|---|
| App Store Connect | Apple's website where you manage your app's details, price, builds and review |
| Apple Developer portal | developer.apple.com: where you create App IDs, certificates and profiles |
| Bundle ID | The app's permanent identity, e.g. `com.yourcompany.myapp` |
| Team ID | The 10-character identity of your developer account |
| Certificate (Apple Distribution) | Your digital signature on the app; valid for 1 year |
| Provisioning Profile | The permit saying which app, which certificate and which capabilities; valid for 1 year |
| API key (.p8) | The key for working with App Store Connect without signing in |
| IPA | An iOS app's install file (like Android's APK/AAB) |
| TestFlight | Apple's system for testing before release |
| XcodeGen | A tool that builds the Xcode project from `project.yml` |
| Codemagic | A service that builds on Macs in the cloud |
| IAP (In-App Purchase) | Purchases inside the app; Non-Consumable = one-time, permanent |
| UMP | Google's SDK for showing the consent form |
| app-ads.txt | A file on your website proving you have the right to sell ads |
| Marketing URL | The website link in the App Store listing; AdMob looks for app-ads.txt here |
| Sandbox | An environment for testing IAP without charging money |
| Guideline 2.1 | The App Review rule: the app must be complete and working / a request for more information |

---

## Appendix C — Template files

The book refers to these template files. They are part of the full Pickixo edition and are not included in this free web edition; the chapters above describe what each one contains, so you can write your own (or ask Claude to, as in Chapter 16).

| File | Purpose | Chapter |
|---|---|---|
| 01-project/project.yml | XcodeGen project (AdMob, test/real IDs, safety script) | 4 |
| 01-project/Info.plist | AdMob, SKAdNetwork, with ATT notes | 4 |
| 01-project/PrivacyInfo.xcprivacy | Privacy manifest | 4 |
| 02-ci/codemagic.yaml | check, simulator and release workflows | 5 |
| 02-ci/github-actions/ios-release.yml | Alternative to Codemagic | 5, 15 |
| 03-website/privacy-policy.html | Privacy Policy (AdMob + IAP) | 7 |
| 03-website/support.html | Support page | 7 |
| 03-website/app-ads.txt | AdMob verification | 7 |
| 04-app-store/store-listing.md | Every field, character limit, rule | 8 |
| 04-app-store/app-privacy-admob.md | Sample App Privacy answers | 6 |
| 04-app-store/app-review-notes.txt | Review Notes | 10 |
| 04-app-store/review-reply-2.1.txt | Reply to 2.1 | 11 |

Each file says at the top what needs changing. Look for the markers `MyApp`, `com.yourcompany`, `YOUR_TEAM_ID`, `XXXX` and put in your own details.

---

**A last word:** publishing your first app is the hardest, because the account, bank, tax, CI and website all have to be set up at once. From your second app on, most of it is already in place. Keep this book close, and check the checklist at every step. Good luck!
