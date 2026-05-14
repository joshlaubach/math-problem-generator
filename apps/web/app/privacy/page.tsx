import { LegalPage } from '@/components/LegalPage'

const PRIVACY = `
## Introduction

Josh Laubach d/b/a Gradient ("Gradient," "we," "our," or "us") operates the Gradient math learning platform at gradient.app (the **"Service"**). This Privacy Policy explains what information we collect, how we use it, with whom we share it, and your rights regarding it.

By using the Service, you agree to the collection and use of information in accordance with this policy.

---

## 1. Information We Collect

### 1.1 Account Information
When you create an account via Clerk, we receive your email address, name, and a unique user identifier. We store your subscription tier, account creation date, and age-confirmation status.

### 1.2 Usage and Learning Data
We collect data about your interactions with the Service, including:
- Math problems generated, topics practiced, and difficulty levels selected
- Answer attempts, correctness, and time taken per problem
- Hint and solution requests
- Calculator usage events
- Tutor session transcripts (for paid tiers)

This data is used to power adaptive difficulty, progress tracking, and platform improvement.

### 1.3 Device and Technical Data
We automatically collect IP address, browser type and version, operating system, referring URLs, and pages visited. This data is used for security, fraud prevention, and service optimization.

### 1.4 Payment Information
Payment details (card number, billing address) are collected and stored exclusively by **Stripe, Inc.** We receive only a tokenized payment reference and subscription status. We never see or store your full payment card details.

### 1.5 Communications
If you contact us by email, we retain those communications to respond to your inquiry and improve our support.

---

## 2. How We Use Your Information

We use the information we collect to:

- Create and manage your account
- Generate and deliver personalized math problems and lesson content
- Track your academic progress and provide adaptive difficulty recommendations
- Process payments and manage subscriptions
- Enforce our Terms of Service and prevent fraud, abuse, and unauthorized access
- Detect bots, automated access, and security threats
- Comply with legal obligations (FERPA, COPPA, CCPA)
- Send transactional emails (account notices, billing receipts, security alerts)
- Improve the Service, train internal quality models, and conduct research (using aggregated, de-identified data only)

We do **not** use your data to serve third-party advertising.

---

## 3. How We Share Your Information

We do not sell, rent, or trade your personal information. We share information only in the following circumstances:

### 3.1 Service Providers
We share data with vendors who help us operate the Service, including:

| Provider | Purpose | Privacy Policy |
|---|---|---|
| Clerk, Inc. | Authentication and identity management | clerk.com/privacy |
| Stripe, Inc. | Payment processing | stripe.com/privacy |
| Anthropic, PBC | AI problem and content generation | anthropic.com/privacy |

These providers are contractually prohibited from using your data for purposes other than providing services to us.

### 3.2 Schools and Teachers
If you are a student enrolled in a classroom on Gradient, your learning data (problems attempted, progress, accuracy) may be visible to the teacher who created that classroom. By joining a classroom, you consent to this sharing.

### 3.3 Legal Requirements
We may disclose information if required to do so by law, regulation, legal process, or government request, or to protect the rights, property, or safety of Gradient, our users, or the public.

### 3.4 Business Transfers
In the event of a merger, acquisition, or sale of assets, your information may be transferred to the successor entity. We will notify you before your data becomes subject to a materially different privacy policy.

---

## 4. Data Retention

We retain your personal information for as long as your account is active or as needed to provide the Service. You may request deletion of your account and associated data at any time by emailing joshlaubach.mathtutor@gmail.com. Upon verified request, we will delete your data within **30 days**, except where retention is required by law or legitimate business necessity (e.g., fraud prevention records, financial transaction records required by applicable law).

---

## 5. Your Privacy Rights

### 5.1 California Residents (CCPA/CPRA)
If you are a California resident, you have the following rights under the California Consumer Privacy Act:

- **Right to Know:** Request disclosure of the categories and specific pieces of personal information we collect, use, and share about you
- **Right to Delete:** Request deletion of your personal information, subject to certain exceptions
- **Right to Correct:** Request correction of inaccurate personal information
- **Right to Opt Out of Sale:** We do not sell personal information. No opt-out is required.
- **Right to Non-Discrimination:** We will not discriminate against you for exercising any of these rights

To exercise these rights, email joshlaubach.mathtutor@gmail.com with the subject line "California Privacy Request." We will respond within **45 days** and may ask you to verify your identity before processing your request.

### 5.2 Nevada Residents
Nevada residents may opt out of the sale of their personal information. We do not sell personal information and therefore no opt-out mechanism is required.

### 5.3 EEA and UK Residents
If you are located in the European Economic Area or United Kingdom, you may have additional rights under the GDPR or UK GDPR, including the right to access, rectify, erase, restrict, or port your data. Contact us at joshlaubach.mathtutor@gmail.com to submit a request. We process your data on the legal basis of contract performance and legitimate interests.

---

## 6. Children's Privacy (COPPA)

The Service is intended for users aged 13 and older. We do not knowingly collect personal information from children under 13. If we discover or are notified that we have collected information from a child under 13, we will immediately delete that information and terminate the associated account.

Parents or guardians who believe their child under 13 has created an account should contact us immediately at joshlaubach.mathtutor@gmail.com.

For users aged 13–17 in jurisdictions that require parental consent (including certain EU member states for users under 16), a parent or guardian must consent to account creation.

---

## 7. Security

We implement reasonable administrative, technical, and physical safeguards to protect your personal information against unauthorized access, alteration, disclosure, or destruction. Authentication is handled by Clerk using industry-standard encryption. Payment data is handled by Stripe using PCI-DSS compliant infrastructure.

No method of transmission over the internet or electronic storage is 100% secure. In the event of a data breach affecting your personal information, we will notify you in accordance with applicable California law.

---

## 8. Cookies and Local Storage

The Service uses cookies and browser local storage to maintain your session, remember your preferences (e.g., dark mode), and detect security threats. We do not use third-party advertising cookies or behavioral tracking cookies.

You may disable cookies in your browser settings, but doing so may impair your ability to use the Service.

---

## 9. Third-Party Links

The Service may contain links to third-party websites. This Privacy Policy does not apply to those sites. We are not responsible for the privacy practices of third parties and encourage you to review their policies.

---

## 10. International Data Transfers

The Service is operated in the United States. If you access the Service from outside the US, your information will be transferred to and processed in the United States, where data protection laws may differ from those in your jurisdiction. By using the Service, you consent to this transfer.

---

## 11. Changes to This Policy

We may update this Privacy Policy from time to time. For material changes, we will provide notice via email or in-app notification at least **30 days** before the change takes effect. Your continued use of the Service after the effective date constitutes acceptance.

---

## 12. Contact Us

For privacy-related questions, requests, or complaints, contact us at:

**Josh Laubach d/b/a Gradient**
Email: joshlaubach.mathtutor@gmail.com

We will respond to all requests within 45 days.
`

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      subtitle="How Gradient collects, uses, and protects your information."
      effectiveDate="May 11, 2026"
      lastUpdated="May 11, 2026"
      content={PRIVACY}
    />
  )
}
