'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth';

export default function HelpPage() {
  const { user } = useAuth();
  const isAthlete = user?.role === 'athlete';
  const backHref = isAthlete ? '/dashboard' : '/training';

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="section-title text-2xl">Help</h1>
        <Link href={backHref} className="text-accent hover:text-accent/80 text-sm font-heading uppercase tracking-wider transition-colors">
          &larr; {isAthlete ? 'Back to Dashboard' : 'Back to Training'}
        </Link>
      </div>

      {/* Athlete Help Section */}
      {isAthlete && (
        <div className="card prose prose-invert max-w-none mb-6">
          <h2 className="font-heading text-xl uppercase tracking-wider text-white mb-6">Athlete Guide</h2>

          <details className="mb-4 group" open>
            <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
                <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
              </svg>
              Getting Started
            </summary>
            <div className="pl-6 pb-2">
              <p className="text-white/80 mb-2">
                Welcome! Your coach has set up your account so you can track your own training and wellness.
              </p>
              <p className="text-white/80">
                From your <strong>Dashboard</strong>, you can see today&apos;s sessions, log wellness, view test results, and export your data.
              </p>
            </div>
          </details>

          <details className="mb-4 group">
            <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
                <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
              </svg>
              Logging a Training Session
            </summary>
            <div className="pl-6 pb-2">
              <ol className="list-decimal list-inside text-white/80 space-y-2">
                <li>Go to <strong>My Training</strong> from the navigation bar.</li>
                <li>Click <strong>&quot;+ Add Session&quot;</strong> (or &quot;+ Add&quot; on mobile).</li>
                <li>Enter the <strong>date</strong>, <strong>training type</strong>, and optionally <strong>RPE</strong> and <strong>duration</strong>.</li>
                <li>Click <strong>&quot;Add Session&quot;</strong> to save.</li>
              </ol>
              <p className="text-white/80 mt-2">
                If you skip RPE and duration, you can add them later by clicking <strong>&quot;Add RPE&quot;</strong> on the session.
              </p>
            </div>
          </details>

          <details className="mb-4 group">
            <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
                <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
              </svg>
              Completing an Assigned Session
            </summary>
            <div className="pl-6 pb-2">
              <p className="text-white/80 mb-2">
                When your coach assigns you a session, it appears with an <strong>&quot;Assigned&quot;</strong> badge.
              </p>
              <ol className="list-decimal list-inside text-white/80 space-y-2">
                <li>Find the assigned session in <strong>My Training</strong> (list or calendar view).</li>
                <li>Click the <strong>&quot;Complete&quot;</strong> button.</li>
                <li>Enter your <strong>RPE</strong> (1-10), <strong>duration</strong> (minutes), and any <strong>notes</strong>.</li>
                <li>Click <strong>&quot;Complete Session&quot;</strong>.</li>
              </ol>
              <p className="text-white/80 mt-2">
                You can also edit exercise reps and weights on assigned sessions by expanding the session row.
              </p>
            </div>
          </details>

          <details className="mb-4 group">
            <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
                <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
              </svg>
              Logging Wellness
            </summary>
            <div className="pl-6 pb-2">
              <p className="text-white/80 mb-2">
                Daily wellness tracking helps your coach monitor your recovery using the <strong>Hooper Index</strong>.
              </p>
              <ol className="list-decimal list-inside text-white/80 space-y-2">
                <li>From the <strong>Dashboard</strong>, use the <strong>&quot;Log Wellness&quot;</strong> quick action, or go to <strong>My Training</strong> and enable the <strong>&quot;Hooper Index&quot;</strong> chart.</li>
                <li>Rate each category 1-7: <strong>Sleep Quality</strong>, <strong>Fatigue</strong>, <strong>Stress</strong>, and <strong>DOMS</strong>.</li>
                <li>Click <strong>&quot;Save&quot;</strong>.</li>
              </ol>
              <p className="text-white/80 mt-2">
                Only one wellness entry per day is allowed. Lower total scores indicate better recovery.
              </p>
            </div>
          </details>

          <details className="mb-4 group">
            <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
                <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
              </svg>
              Viewing Your Data
            </summary>
            <div className="pl-6 pb-2">
              <ul className="list-disc list-inside text-white/80 space-y-2">
                <li><strong>Testing</strong> — View your jump assessments, mobility screenings, isometrics, and air bike test results.</li>
                <li><strong>My Profile</strong> — View your personal details (managed by your coach).</li>
                <li><strong>Export My Data</strong> — Download all your data as JSON from the Dashboard or your Profile page.</li>
              </ul>
            </div>
          </details>
        </div>
      )}

      {/* Coach Help Section */}
      {!isAthlete && (
      <div className="card prose prose-invert max-w-none">
        <h2 className="font-heading text-xl uppercase tracking-wider text-white mb-6">User Manual — Athletes &amp; Training</h2>

        <details className="mb-4 group" open>
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Getting Started
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              As a coach, your core workflow is: create athletes, log their training sessions and wellness,
              run performance tests, and track progress over time.
            </p>
            <p className="text-white/80">
              Start by adding your first athlete, then explore the Training, Testing, and Library sections
              from the navigation bar.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Adding an Athlete
          </summary>
          <div className="pl-6 pb-2">
            <ol className="list-decimal list-inside text-white/80 space-y-2">
              <li>Navigate to any page that shows the athlete selector in the header (e.g. Training or Testing).</li>
              <li>Click the athlete selector dropdown in the top centre of the page.</li>
              <li>Click the <strong>&quot;+ Add Athlete&quot;</strong> button at the bottom of the dropdown.</li>
              <li>Fill in the required fields: <strong>First Name</strong>, <strong>Surname</strong>, and <strong>Gender</strong>. Date of birth is optional.</li>
              <li>Click <strong>&quot;Create&quot;</strong>.</li>
            </ol>
            <p className="text-white/80 mt-2">
              The new athlete will be automatically selected. You can also bulk-create athletes by uploading
              a CSV file from the Upload page — athletes are auto-created from names in the file.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Editing Athlete Details
          </summary>
          <div className="pl-6 pb-2">
            <ol className="list-decimal list-inside text-white/80 space-y-2">
              <li>Select the athlete from the dropdown in the header.</li>
              <li>Click the <strong>pencil icon</strong> that appears next to the selected athlete&apos;s name in the dropdown. This takes you to the Athlete Information page.</li>
              <li>Edit any of the available fields:
                <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                  <li><strong>First Name</strong> and <strong>Surname</strong></li>
                  <li><strong>Gender</strong> (male / female)</li>
                  <li><strong>Date of Birth</strong></li>
                  <li><strong>Body Mass (kg)</strong> and <strong>Stature (cm)</strong></li>
                  <li><strong>Status</strong> (active / injured / inactive)</li>
                  <li><strong>Notes</strong> — free-text field for any additional information</li>
                </ul>
              </li>
              <li>Click <strong>&quot;Save Profile&quot;</strong> to save your changes.</li>
            </ol>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Generating an Invite Code
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Invite codes let athletes create their own account and link it to your coaching roster.
            </p>
            <ol className="list-decimal list-inside text-white/80 space-y-2">
              <li>Select the athlete, then go to the <strong>Athlete Information</strong> page (pencil icon in the athlete dropdown).</li>
              <li>Scroll down to the <strong>&quot;Athlete Portal Access&quot;</strong> section.</li>
              <li>Click <strong>&quot;Generate Invite Code&quot;</strong>.</li>
              <li>Copy the generated link and share it with your athlete (e.g. via message or email).</li>
            </ol>
            <p className="text-white/80 mt-2">
              The athlete uses the link to create an account with their email and password. Once signed up,
              they are automatically linked to your roster and can view their own data, log training sessions,
              and record wellness entries. Invite codes expire after <strong>7 days</strong>.
            </p>
          </div>
        </details>

        <h2 className="font-heading text-xl uppercase tracking-wider text-white mt-8 mb-4 pt-6 border-t border-white/10">Training</h2>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Calendar &amp; List Views
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              The Training page has two views, toggled with the icons in the top-right corner:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-2">
              <li><strong>Calendar View</strong> — a monthly calendar showing session dots on each day. Click a day to see that day&apos;s sessions. Colour-coded: completed sessions, assigned sessions awaiting completion, and regular logged sessions.</li>
              <li><strong>List View</strong> — a chronological table of all sessions with full detail, including training type, RPE, duration, sRPE, and exercise breakdowns. Supports inline editing and deletion.</li>
            </ul>
            <p className="text-white/80 mt-2">
              Both views show the same data — use whichever suits your workflow. Your preference is remembered between visits.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Readiness Indicator
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              The traffic-light indicator at the top of the Training page shows the athlete&apos;s current readiness to train. It combines <strong>two</strong> independent measures:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-2 mb-3">
              <li><strong>ACWR</strong> (Acute:Chronic Workload Ratio) — from training load data</li>
              <li><strong>Hooper Index</strong> — from wellness questionnaire data</li>
            </ul>
            <p className="text-white/80 mb-2">Each measure is scored, then averaged to produce the final readiness level:</p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><span className="text-green-400 font-semibold">Green</span> — Good to Go (optimal ACWR + good recovery)</li>
              <li><span className="text-yellow-400 font-semibold">Amber</span> — Caution (moderate load or recovery concerns)</li>
              <li><span className="text-red-400 font-semibold">Red</span> — High Risk (excessive load or poor recovery)</li>
              <li><span className="text-white/40 font-semibold">Grey</span> — No Data (insufficient sessions or wellness entries)</li>
            </ul>
            <p className="text-white/80">
              To get a readiness reading, the athlete needs both <strong>training sessions with RPE and duration</strong> (for ACWR) and <strong>wellness entries</strong> (for the Hooper Index). Without both, the indicator shows &quot;No Data&quot; or uses whichever measure is available.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Hooper Index (Wellness)
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              The Hooper Index is a validated wellness questionnaire used to monitor athlete recovery. It captures <strong>4 scores</strong>, each rated 1–7:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><strong>Sleep Quality</strong> (1 = very good, 7 = very bad)</li>
              <li><strong>Fatigue</strong> (1 = very low, 7 = very high)</li>
              <li><strong>Stress</strong> (1 = very low, 7 = very high)</li>
              <li><strong>DOMS</strong> — Delayed Onset Muscle Soreness (1 = very low, 7 = very high)</li>
            </ul>
            <p className="text-white/80 mb-2">
              The <strong>Hooper Index total</strong> is the sum of all 4 scores (range: 4–28). Lower is better:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><span className="text-green-400 font-semibold">4–10</span> — Good recovery</li>
              <li><span className="text-yellow-400 font-semibold">11–16</span> — Moderate (monitor closely)</li>
              <li><span className="text-red-400 font-semibold">17–28</span> — Poor recovery (consider reducing load)</li>
            </ul>
            <p className="text-white/80 mb-2">
              To log wellness, click <strong>&quot;+ Add Wellness&quot;</strong> on the Training page. Only one entry per athlete per day is allowed. The Hooper Index chart (toggled via the &quot;Hooper Index&quot; checkbox below the sessions view) shows a stacked bar chart of the last 14 entries, making trends easy to spot.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Training Load (ACWR)
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Training load is calculated from <strong>sRPE</strong> (session Rating of Perceived Exertion):
            </p>
            <p className="text-white/60 text-sm mb-3 pl-4 border-l-2 border-accent/30">
              sRPE = RPE (1–10) &times; Session Duration (minutes)
            </p>
            <p className="text-white/80 mb-2">
              The Training Load chart (toggled via the &quot;Training Load&quot; checkbox below the sessions view) shows a 28-day bar chart of daily sRPE, along with four key metrics:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-2 mb-3">
              <li><strong>Weekly Load</strong> — total sRPE over the last 7 days</li>
              <li><strong>Monotony</strong> — how uniform the training is (mean &divide; standard deviation over 7 days). Above 2.0 suggests insufficient variation and increased injury risk</li>
              <li><strong>Strain</strong> — weekly load &times; monotony. Above 6,000 is associated with increased illness risk</li>
              <li><strong>ACWR</strong> (Acute:Chronic Workload Ratio) — 7-day average load divided by 28-day average load. The key metric for readiness:
                <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                  <li><span className="text-green-400 font-semibold">0.8–1.3</span> — Optimal (sweet spot)</li>
                  <li><span className="text-yellow-400 font-semibold">Below 0.8 or 1.3–1.5</span> — Caution (undertraining or building too fast)</li>
                  <li><span className="text-red-400 font-semibold">Above 1.5</span> — Danger zone (high injury risk from load spike)</li>
                </ul>
              </li>
            </ul>
            <p className="text-white/80">
              For accurate ACWR readings, you need at least 4 weeks of consistent session logging with RPE and duration recorded.
            </p>
          </div>
        </details>

        <h2 className="font-heading text-xl uppercase tracking-wider text-white mt-8 mb-4 pt-6 border-t border-white/10">Library</h2>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Add Exercise (Overview)
          </summary>
          <div className="pl-6 pb-2">
            <ol className="list-decimal list-inside text-white/80 space-y-2">
              <li>Navigate to <strong>Library</strong> &rarr; <strong>Exercises</strong> tab.</li>
              <li>Click <strong>&quot;+ Add Exercise&quot;</strong>.</li>
              <li>Choose a <strong>Category</strong> from the dropdown — this determines which fields appear on the form.</li>
              <li>Fill in the exercise details and click <strong>&quot;Save&quot;</strong>.</li>
            </ol>
            <p className="text-white/80 mt-2">
              Exercise names must be <strong>unique within your account</strong>. The four categories are Strength, Plyometric, Conditioning, and Other — each described below.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Strength Exercises
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Strength exercises use a per-set layout where you configure each set individually.
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><strong>Exercise Name</strong> — e.g. Back Squat, Bench Press</li>
              <li><strong>Category</strong> — select <strong>&quot;Strength&quot;</strong></li>
              <li><strong>Number of Sets</strong> — use the +/&minus; stepper to add or remove sets</li>
              <li><strong>Per-set cards</strong> — each set has its own <strong>Reps</strong> and <strong>Weight (kg)</strong> fields</li>
              <li><strong>Default Rest (s)</strong> — rest period between sets</li>
              <li><strong>Notes</strong> — optional free-text field</li>
            </ul>
            <p className="text-white/60 text-sm pl-4 border-l-2 border-accent/30">
              Example: Back Squat — 3 sets of 5 reps at 80 / 85 / 90 kg, 180s rest between sets.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Plyometric Exercises
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Plyometric exercises use the same per-set layout as Strength.
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><strong>Exercise Name</strong> — e.g. Box Jump, Depth Jump</li>
              <li><strong>Category</strong> — select <strong>&quot;Plyometric&quot;</strong></li>
              <li><strong>Number of Sets</strong> — use the +/&minus; stepper</li>
              <li><strong>Per-set cards</strong> — <strong>Reps</strong> and <strong>Weight (kg)</strong> for each set (weight is optional for bodyweight plyometrics)</li>
              <li><strong>Default Rest (s)</strong> and <strong>Notes</strong> (optional)</li>
            </ul>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Conditioning Exercises
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Conditioning exercises have a different form layout focused on per-rep intervals rather than per-set weight.
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><strong>Exercise Name</strong> — e.g. HIIT Sprints, Assault Bike Intervals</li>
              <li><strong>Category</strong> — select <strong>&quot;Conditioning&quot;</strong></li>
              <li><strong>Default Reps</strong> — number of reps per set</li>
              <li><strong>Intensity Type</strong> — choose from <strong>&quot;RPE&quot;</strong>, <strong>&quot;Speed (km/h)&quot;</strong>, or <strong>&quot;Power (W)&quot;</strong></li>
              <li><strong>Intensity Value</strong> — the target value for the chosen intensity type</li>
              <li><strong>Work Duration (s)</strong> — how long each rep lasts</li>
              <li><strong>Rest Between Reps (s)</strong> — recovery between individual reps</li>
              <li><strong>Rest Between Sets (s)</strong> — recovery between sets</li>
              <li><strong>Notes</strong> — optional</li>
            </ul>
            <p className="text-white/60 text-sm pl-4 border-l-2 border-accent/30">
              Example: HIIT Sprints — 6 reps, Speed 15 km/h, 30s work duration, 30s rest between reps.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Other Exercises
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              The &quot;Other&quot; category uses the same per-set form as Strength and Plyometric. Use it for exercises that don&apos;t fit the other categories — e.g. mobility drills, warm-up circuits, or core work.
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1">
              <li><strong>Exercise Name</strong>, <strong>Number of Sets</strong>, per-set <strong>Reps</strong> and <strong>Weight (kg)</strong></li>
              <li><strong>Default Rest (s)</strong> and <strong>Notes</strong> (optional)</li>
            </ul>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Session Templates (Overview)
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Templates are reusable session plans with pre-configured exercises. Instead of rebuilding the same session from scratch each time, create a template once and apply it to any training session.
            </p>
            <ol className="list-decimal list-inside text-white/80 space-y-2">
              <li>Navigate to <strong>Library</strong> &rarr; <strong>Templates</strong> tab.</li>
              <li>Click <strong>&quot;+ Create Template&quot;</strong>.</li>
              <li>Fill in the fields:
                <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                  <li><strong>Template Name</strong> (required)</li>
                  <li><strong>Training Type</strong> — e.g. Strength, Conditioning, or a custom type</li>
                  <li><strong>Notes</strong> (optional)</li>
                </ul>
              </li>
              <li>Add exercises using the library autocomplete — defaults auto-populate from your exercise library.</li>
              <li>Reorder exercises with the <strong>&#9650;/&#9660;</strong> buttons.</li>
              <li>Click <strong>&quot;Save&quot;</strong>.</li>
            </ol>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Template Exercises
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Each exercise row in a template contains the following fields:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><strong>Exercise Name</strong> — type to search your library, or enter a new name</li>
              <li><strong>Sets</strong>, <strong>Reps</strong>, <strong>Weight (kg)</strong></li>
              <li>Conditioning exercises also show: <strong>Intensity Type/Value</strong>, <strong>Duration</strong>, <strong>Rest Between Reps</strong></li>
            </ul>
            <p className="text-white/80 mb-2">
              Click <strong>&quot;+ Add Exercise Row&quot;</strong> to add more exercises, or the <strong>&times;</strong> button to remove one. Selecting an exercise from the library autocomplete pre-fills its default values (category, reps, weight, rest, etc.).
            </p>
            <p className="text-white/80">
              A minimum of <strong>1 exercise</strong> is required to save a template.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Applying Templates to Sessions
          </summary>
          <div className="pl-6 pb-2">
            <ol className="list-decimal list-inside text-white/80 space-y-2">
              <li>Open a training session and expand the exercises section.</li>
              <li>Click <strong>&quot;Import from Template&quot;</strong> (next to &quot;+ Add Exercise&quot;).</li>
              <li>Browse your available templates and click <strong>&quot;Apply&quot;</strong>.</li>
            </ol>
            <p className="text-white/80 mt-3 mb-2">
              Applying a template <strong>replaces all exercises</strong> in the session with the template&apos;s exercises. After applying, you can edit individual sets, reps, and weights as needed.
            </p>
            <p className="text-white/60 text-sm pl-4 border-l-2 border-accent/30">
              Tip: Create templates for recurring session types (e.g. &quot;Upper Body Strength&quot;, &quot;Sprint Conditioning&quot;) to speed up session planning.
            </p>
          </div>
        </details>

        <h2 className="font-heading text-xl uppercase tracking-wider text-white mt-8 mb-4 pt-6 border-t border-white/10">Testing</h2>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Jump Assessments
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              The Jump tab on the Testing page is the primary view for countermovement jump (CMJ) and squat jump (SJ) performance data. It tracks <strong>6 metrics</strong>:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><strong>CMJ Height (cm)</strong> — countermovement jump height</li>
              <li><strong>SJ Height (cm)</strong> — squat jump height</li>
              <li><strong>EUR (cm)</strong> — Eccentric Utilisation Ratio (auto-calculated: CMJ &minus; SJ)</li>
              <li><strong>RSI</strong> — Reactive Strength Index (auto-calculated: Flight Time &divide; Contact Time)</li>
              <li><strong>Flight Time (ms)</strong></li>
              <li><strong>Contact Time (ms)</strong></li>
            </ul>
            <p className="text-white/80 mb-2">
              Use the metric dropdown to switch between metrics. The page has two views:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-2 mb-3">
              <li><strong>Table View</strong> — sortable performance table showing each test event with benchmark comparisons (Z-scores). Click any row to edit or delete the event inline.</li>
              <li><strong>Graph View</strong> — line chart showing the athlete&apos;s performance trend over time for the selected metric.</li>
            </ul>
            <p className="text-white/80 mb-2">
              The <strong>Reference Group</strong> toggle lets you compare the athlete against different benchmarks:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><strong>Cohort</strong> — all athletes in your dataset</li>
              <li><strong>Gender</strong> — male or female cohort</li>
              <li><strong>Mass Band</strong> — weight category (e.g. 60&ndash;70 kg)</li>
            </ul>
            <p className="text-white/80">
              Click <strong>&quot;Generate Radar Plot&quot;</strong> to see a Z-score radar chart across all available metrics for the selected date. The radar uses colour-coded dots and zone bands to show strengths and weaknesses at a glance.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Mobility Assessments
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Mobility assessments use the NASM overhead squat assessment protocol to identify movement compensations.
            </p>
            <ol className="list-decimal list-inside text-white/80 space-y-2 mb-3">
              <li>Navigate to <strong>Testing</strong> &rarr; <strong>Mobility</strong> tab.</li>
              <li>Click <strong>&quot;+ New Assessment&quot;</strong>.</li>
              <li>Choose the assessment type: <strong>Overhead Squat</strong>, <strong>Single Leg Squat (Left)</strong>, or <strong>Single Leg Squat (Right)</strong>.</li>
              <li>Work through the <strong>NASM checklist</strong> — checkboxes organised by body region:
                <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                  <li><strong>Feet</strong>, <strong>Knees</strong>, <strong>LPHC</strong> (Lumbo-Pelvic-Hip Complex), <strong>Shoulders</strong>, <strong>Head</strong></li>
                </ul>
              </li>
              <li>For each finding, select: <strong>Severity</strong> (Mild / Moderate / Significant) and <strong>Side</strong> (Left / Right / Bilateral).</li>
              <li>Optionally upload <strong>photos</strong> — anterior, lateral, and posterior views (10 MB limit per photo).</li>
              <li>Click <strong>&quot;Save&quot;</strong>.</li>
            </ol>
            <p className="text-white/80">
              A <strong>summary</strong> is auto-generated from your checklist findings, listing all observed compensations with severity and side for quick reference.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Isometric Assessments
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              The Isometrics tab works the same way as Jump Assessments but is filtered to isometric-specific metrics (e.g. peak force, rate of force development).
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-2 mb-3">
              <li><strong>Table View</strong> and <strong>Graph View</strong> — same layout and functionality as the Jump tab</li>
              <li><strong>Reference Groups</strong> — Cohort, Gender, and Mass Band comparisons</li>
              <li><strong>Radar Plot</strong> — Z-score radar across isometric metrics</li>
              <li>Click <strong>&quot;+ Add Data&quot;</strong> to log new isometric test results</li>
            </ul>
            <p className="text-white/60 text-sm pl-4 border-l-2 border-accent/30">
              Isometric data can also be uploaded via CSV from the Upload page, using the same format with isometric metric columns.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Air Bike 30s Sprint Test
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              The Air Bike test measures anaerobic power output and fatigue characteristics using a 30-second sprint protocol.
            </p>
            <ol className="list-decimal list-inside text-white/80 space-y-2 mb-3">
              <li>Navigate to <strong>Testing</strong> &rarr; <strong>Air Bike</strong> tab.</li>
              <li>Click <strong>&quot;+ New Test&quot;</strong>.</li>
              <li>Enter the athlete&apos;s <strong>Body Mass (kg)</strong>.</li>
              <li>Enter <strong>Sprint 1</strong> power values at three time points: <strong>7s</strong>, <strong>14s</strong>, and <strong>27s</strong> (all required).</li>
              <li><strong>Sprint 2</strong> is optional — if entered, all three time points (7s, 14s, 27s) are required.</li>
              <li><strong>Blood Lactate</strong> is optional for each sprint.</li>
              <li>Click <strong>&quot;Save&quot;</strong>.</li>
            </ol>
            <p className="text-white/80 mb-2">
              Expand a test row to see:
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-1 mb-3">
              <li><strong>Power decay chart</strong> — Sprint 1 (cyan) and Sprint 2 (amber) curves showing power drop-off over 30 seconds</li>
              <li><strong>Summary stats</strong> — peak power, W/kg, and drop-off percentages</li>
              <li><strong>Within-sprint decay</strong> — how much power drops within each sprint (7s &rarr; 14s &rarr; 27s)</li>
              <li><strong>Between-sprint comparison</strong> — Sprint 2 values as a percentage of Sprint 1 peak power</li>
            </ul>
          </div>
        </details>

        <h2 className="font-heading text-xl uppercase tracking-wider text-white mt-8 mb-4 pt-6 border-t border-white/10">Reports</h2>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Creating a Test Report
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              Test reports consolidate an athlete&apos;s assessment data into a single document for review or sharing. Only <strong>coaches</strong> and <strong>admins</strong> can create reports.
            </p>
            <ol className="list-decimal list-inside text-white/80 space-y-2 mb-3">
              <li>Navigate to the <strong>Test Report</strong> page from the navigation bar.</li>
              <li>Select an <strong>athlete</strong> from the dropdown.</li>
              <li>Set the <strong>Report Date</strong> (defaults to today). Optionally set <strong>Date Range Start</strong> and <strong>Date Range End</strong> to filter which data is included.</li>
              <li>Toggle report sections on or off using the <strong>4 checkboxes</strong> (all enabled by default):
                <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                  <li><strong>Jump Assessments</strong></li>
                  <li><strong>Isometrics</strong></li>
                  <li><strong>Mobility Assessments</strong></li>
                  <li><strong>Air Bike</strong></li>
                </ul>
              </li>
              <li>Add notes: an <strong>Overall Summary</strong> at the top, plus <strong>per-section notes</strong> for each enabled section.</li>
              <li>Click <strong>&quot;Generate Preview&quot;</strong> to fetch data and render the report.</li>
            </ol>
            <p className="text-white/60 text-sm pl-4 border-l-2 border-accent/30">
              At least 1 section must be enabled to generate a preview.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Preview &amp; PDF Export
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              After clicking &quot;Generate Preview&quot;, the report renders with a header showing the athlete&apos;s <strong>name</strong>, <strong>gender</strong>, <strong>body mass</strong>, <strong>stature</strong>, <strong>report date</strong>, and <strong>date range</strong>.
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-2 mb-3">
              <li>Each enabled section shows the athlete&apos;s latest data: tables with values and Z-scores, charts, and photos where applicable.</li>
              <li>Sections with no data for the selected period display <strong>&quot;No data available for this period&quot;</strong>.</li>
              <li>Click <strong>&quot;Export PDF&quot;</strong> to download an A4 PDF with one section per page.</li>
              <li>Click <strong>&quot;Back to Settings&quot;</strong> to return to the configuration screen and adjust dates, sections, or notes.</li>
            </ul>
            <p className="text-white/60 text-sm pl-4 border-l-2 border-accent/30">
              The PDF is named <strong>{'{AthleteName}'}_Test_Report_{'{Date}'}.pdf</strong> and is generated client-side — no data leaves your browser.
            </p>
          </div>
        </details>

        <details className="mb-4 group">
          <summary className="text-2xl font-heading text-white mb-3 cursor-pointer list-none flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent transition-transform group-open:rotate-90">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            Saving &amp; Managing Reports
          </summary>
          <div className="pl-6 pb-2">
            <p className="text-white/80 mb-2">
              You can save report configurations to reuse later, rather than reconfiguring dates, sections, and notes each time.
            </p>
            <ul className="list-disc list-inside text-white/80 space-y-2 mb-3">
              <li>Click <strong>&quot;Save Report&quot;</strong> to persist the current configuration (dates, enabled sections, and notes) in the database.</li>
              <li>Saved reports appear in a list below the configuration form with <strong>&quot;Load&quot;</strong> and <strong>&quot;Delete&quot;</strong> buttons.</li>
              <li>Click <strong>&quot;Load&quot;</strong> to reload a saved report&apos;s settings into the form.</li>
              <li>In preview mode, click <strong>&quot;Update Report&quot;</strong> to overwrite an existing saved report with the current settings.</li>
            </ul>
            <p className="text-white/60 text-sm pl-4 border-l-2 border-accent/30">
              Report configs are saved — not the PDF itself. The PDF is generated fresh each time from the latest data, so reports always reflect the most up-to-date results.
            </p>
          </div>
        </details>

        <div className="border-t border-white/10 pt-4 mt-6">
          <p className="text-white/40 text-sm">
            More sections coming soon.
          </p>
        </div>
      </div>
      )}
    </div>
  );
}
