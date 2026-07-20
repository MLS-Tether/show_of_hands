import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api'
import { keys } from '../../queries'

const READINESS_LABELS = {
  ready: 'Ready',
  review_first: 'Review first',
  mixed: 'Mixed readiness',
}

function AssignmentFitResult({ sectionId, result }) {
  const queryClient = useQueryClient()
  const [postedUrls, setPostedUrls] = useState([])
  const [postError, setPostError] = useState('')
  const [postingUrl, setPostingUrl] = useState(null)

  if (!result) return null
  const { ai_available: aiAvailable, unavailable_reason: reason, verdict, stats } = result

  async function postToResources(resource) {
    setPostError('')
    setPostingUrl(resource.url)
    try {
      await api.post(`/sections/${sectionId}/resources`, {
        title: resource.title,
        url: resource.url,
        description: resource.why,
      })
      queryClient.invalidateQueries({ queryKey: keys.sectionResources(sectionId) })
      setPostedUrls((prev) => [...prev, resource.url])
    } catch {
      setPostError('Could not post resource.')
    } finally {
      setPostingUrl(null)
    }
  }

  return (
    <div className="fit-result">
      {aiAvailable && verdict && (
        <>
          <div className={`fit-badge fit-badge-${verdict.readiness}`}>
            {READINESS_LABELS[verdict.readiness] || verdict.readiness}
          </div>
          <p className="fit-rationale">{verdict.rationale}</p>
          {verdict.topics_to_review.length > 0 && (
            <p className="fit-topics">
              Review first: {verdict.topics_to_review.join(', ')}
            </p>
          )}
          {verdict.suggested_resources.length > 0 && (
            <div className="fit-resources">
              <div className="widget-label">suggested resources (vet before sharing)</div>
              {verdict.suggested_resources.map((r, index) => (
                <div className="fit-resource-row" key={`${r.url}-${index}`}>
                  <span>
                    <a href={r.url} target="_blank" rel="noopener noreferrer">
                      {r.title}
                    </a>
                    <div className="teacher-panel-row-sub">{r.why}</div>
                  </span>
                  {postedUrls.includes(r.url) ? (
                    <span className="teacher-panel-row-sub">Posted ✓</span>
                  ) : (
                    <button
                      type="button"
                      className="teacher-panel-button"
                      disabled={postingUrl !== null}
                      onClick={() => postToResources(r)}
                    >
                      {postingUrl === r.url ? 'Posting…' : 'Post to resources'}
                    </button>
                  )}
                </div>
              ))}
              {postError && <p className="teacher-panel-error">{postError}</p>}
            </div>
          )}
        </>
      )}

      {!aiAvailable && (
        <p className="fit-unavailable">
          {reason === 'insufficient_data'
            ? 'Not enough graded work yet for an AI readiness check.'
            : 'AI analysis unavailable right now — showing class stats only.'}
        </p>
      )}

      <div className="fit-stats">
        <div className="widget-label">class stats used</div>
        <p className="teacher-panel-row-sub">
          {stats.enrolled_count} enrolled · {stats.graded_submission_count} graded submissions
        </p>
        {Object.keys(stats.category_averages).length > 0 && (
          <p className="teacher-panel-row-sub">
            Averages:{' '}
            {Object.entries(stats.category_averages)
              .map(([category, avg]) => `${category} ${avg}%`)
              .join(' · ')}
          </p>
        )}
        {stats.help_request_topics.length > 0 && (
          <p className="teacher-panel-row-sub">
            Help requested on:{' '}
            {stats.help_request_topics.map((t) => `${t.topic} (${t.count})`).join(', ')}
          </p>
        )}
      </div>
    </div>
  )
}

export default AssignmentFitResult
