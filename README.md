Cosmetic Detective 🧴🔍

A cross-platform mobile application (iOS + Android) inspired by 维鉴.
Users upload photos of cosmetics, and part-time reviewers verify authenticity and send results back.

📂 Project Structure
cosmetic_detective/
│
├── mobile/    # Expo / React Native app (iOS & Android)
│
├── console/   # Next.js reviewer/admin web console
│
├── cloud/     # Firebase backend (functions + security rules)
│
└── README.md  # This file

mobile/

Built with Expo + React Native (TypeScript).

Features: user auth, ticket submission (photos + notes), ticket list/detail, chat, push notifications.

console/

Built with Next.js (TypeScript), deployed to Vercel.

Features: reviewer login, ticket queue, image viewer, verdict submission, chat, admin dashboards.

cloud/

Firebase Cloud Functions + Security Rules.

Features: ticket lifecycle automations, push notifications, SLA timers, access control.

🚀 Getting Started
Prerequisites

Node.js (LTS) + npm or yarn

Expo CLI (npm install -g expo-cli)

Firebase account + projects (dev, staging, prod)

Apple Developer + Google Play accounts (for distribution)

Setup

Clone the repo:

git clone git@github.com:YOUR_USERNAME/cosmetic_detective.git
cd cosmetic_detective


Install dependencies for each subproject:

cd mobile && npm install
cd ../console && npm install
cd ../cloud/functions && npm install

🌐 Environments

Dev → local builds, wide-open rules, test data only.

Staging → TestFlight/Play internal testing, production-like rules.

Production → live users, strict rules, monitoring enabled.

Each Firebase project has:

Firestore (tickets, messages, results)

Storage (images)

Auth (users, reviewers, admins)

Functions (triggers & automations)

Cloud Messaging (push notifications)

📌 Roadmap (MVP)

 User auth (login/logout)

 Submit ticket (1–5 images, brand, category, notes)

 Ticket list + detail + live status

 Reviewer console (claim, inspect, verdict, chat)

 Push notifications

 Secure storage & Firestore rules

📜 License

TBD — private for now (default all rights reserved).

✨ Tagline: Upload. Verify. Shop with confidence.