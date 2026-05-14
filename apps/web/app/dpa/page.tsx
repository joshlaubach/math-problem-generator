import { LegalPage } from '@/components/LegalPage'

const DPA = `
> **For Schools and Teachers:** This Data Processing Agreement governs how Gradient handles student data when the Service is used in a classroom or institutional setting. By enabling classroom features, the School (as defined below) agrees to the terms of this DPA on behalf of itself and its students.

---

## 1. Introduction and Scope

This Data Processing Agreement ("DPA") is entered into between **Josh Laubach d/b/a Gradient** ("Operator") and the educational institution, school district, or teacher enabling classroom features on the Service ("School"). This DPA forms part of and is incorporated into Gradient's Terms of Service.

This DPA applies only when the Service is used in a context that causes Gradient to receive, store, or process Student Data (as defined below) on behalf of a School. It does not apply to individual students using the Service independently outside of an institutional relationship.

---

## 2. Definitions

- **Student Data** means any personally identifiable information (PII) directly related to a student that is provided to or collected by Gradient in the course of the student's use of the Service, including name, email address, academic performance data, problem attempts, and progress records.
- **School Official** means a teacher, administrator, or other authorized School employee who has a legitimate educational interest in Student Data under FERPA.
- **FERPA** means the Family Educational Rights and Privacy Act, 20 U.S.C. § 1232g.
- **COPPA** means the Children's Online Privacy Protection Act, 15 U.S.C. §§ 6501–6506.
- **Authorized User** means a student whose School has enrolled them in a Gradient classroom.

---

## 3. Designation as School Official

The School designates Gradient as a **School Official** with a legitimate educational interest under FERPA for the purpose of providing the Service. Gradient agrees to use Student Data only for the purpose of providing and improving the Service as directed by the School, consistent with this designation.

---

## 4. Collection and Permitted Uses of Student Data

Gradient collects and processes Student Data solely to:

- Create and maintain student accounts within the School's classroom
- Generate personalized math problems, hints, and solutions
- Track individual student progress and provide performance analytics to teachers
- Operate adaptive difficulty and spaced-repetition features
- Diagnose and fix technical problems affecting the Service

Gradient will **not**:

- Use Student Data to serve targeted advertising to students
- Build individual profiles of students for purposes other than providing the Service
- Sell, rent, lease, or trade Student Data to any third party
- Disclose Student Data except as permitted by this DPA, FERPA, and applicable law
- Retain Student Data beyond the period necessary to provide the Service (see Section 8)

---

## 5. Obligations of the School

The School represents, warrants, and agrees that:

- It has the legal authority to enter into this DPA on behalf of itself and its students
- It has provided all required notices to students and parents and obtained all required consents under FERPA, COPPA, and applicable state law before enrolling students in a Gradient classroom
- It will ensure that only School Officials access Student Data through teacher accounts, and will promptly deactivate accounts of departing personnel
- It will notify Gradient promptly if any student enrolled in a Gradient classroom is under 13, so that appropriate COPPA protections can be applied
- It will use the Service only for lawful educational purposes in compliance with all applicable laws

---

## 6. Obligations of Gradient

Gradient agrees to:

- Process Student Data only as directed by the School and as described in this DPA
- Implement and maintain reasonable administrative, technical, and physical safeguards appropriate to the nature and sensitivity of Student Data
- Notify the School within **72 hours** of becoming aware of a confirmed data breach involving Student Data
- Provide the School with access to Student Data upon request to support the School's obligations to students and parents under FERPA
- Delete or return Student Data upon termination of the relationship as described in Section 8

---

## 7. Subprocessors

Gradient shares Student Data with the following subprocessors solely to provide the Service:

| Subprocessor | Purpose | Location |
|---|---|---|
| Clerk, Inc. | Authentication and session management | United States |
| Anthropic, PBC | AI-generated problem and hint content | United States |

Gradient does not share Student Data with Stripe, Inc. except where a School or teacher holds a paid subscription (in which case only billing contact information, not Student Data, is shared).

Gradient will provide **30 days' prior notice** before adding a new subprocessor that will process Student Data. The School may object to a new subprocessor within that period; if the parties cannot reach agreement, the School may terminate this DPA without penalty.

---

## 8. Data Retention and Deletion

Upon termination of the School's use of classroom features, or upon written request from the School, Gradient will:

- Delete all Student Data associated with that School's classrooms within **30 days**
- Provide a confirmation of deletion upon request

Gradient may retain de-identified, aggregated data derived from Student Data (from which no individual student can be identified) for service improvement purposes after deletion.

Individual students may also request deletion of their data in accordance with Gradient's Privacy Policy.

---

## 9. Parental and Student Rights

Gradient supports the School's obligations to honor parental and student rights under FERPA and COPPA, including:

- **Right to Inspect:** Parents and eligible students (18+) may request access to Student Data held by Gradient by contacting joshlaubach.mathtutor@gmail.com
- **Right to Correct:** Requests to correct inaccurate Student Data should be directed to the School, which may then direct Gradient to make corrections
- **Right to Delete:** Parents may request deletion of their child's Student Data by contacting joshlaubach.mathtutor@gmail.com

Gradient will respond to verified requests within **45 days**.

---

## 10. Security Incident Notification

In the event of a security incident that results in, or is reasonably likely to result in, unauthorized access to Student Data, Gradient will:

1. Notify the School's designated contact within **72 hours** of confirming the incident
2. Provide a written summary of the nature of the incident, data affected, and remediation steps taken
3. Cooperate with the School's investigation and reasonable remediation requests

---

## 11. Term and Termination

This DPA is effective upon the School's acceptance (by enabling classroom features) and continues for as long as the School uses Gradient's classroom features. Either party may terminate this DPA upon **30 days' written notice**. Termination of this DPA terminates the School's right to use classroom features but does not affect individual student accounts.

---

## 12. Certifications

By enabling classroom features, the authorized School representative certifies that:

1. They are authorized to bind the School to this DPA
2. The School has complied or will comply with all applicable notice and consent requirements before enrolling students
3. The School will use the Service in compliance with FERPA, COPPA, and all applicable state student data privacy laws (including the California Student Privacy Alliance (CSPA) framework where applicable)

---

## 13. Contact

For questions about this DPA, student data requests, or data breach notification, contact:

**Josh Laubach d/b/a Gradient**
Email: joshlaubach.mathtutor@gmail.com

Schools requiring a countersigned copy of this DPA for their records should email the above address with the subject line "DPA Countersignature Request."
`

export default function DPAPage() {
  return (
    <LegalPage
      title="Data Processing Agreement"
      subtitle="For schools and teachers using Gradient in a classroom setting."
      effectiveDate="May 11, 2026"
      lastUpdated="May 11, 2026"
      content={DPA}
    />
  )
}
