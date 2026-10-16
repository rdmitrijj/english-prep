import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router";
import { api, type Attempt, type AttemptSection, type Feedback } from "../api";
import "../exam/exam.css";
import QuestionGroup from "../exam/Questions";
import ReadingView from "../exam/ReadingView";
import { isAnswered, useResponses } from "../exam/useResponses";
import { qtypeLabel } from "../labels";
import FeedbackPanel, { showEvidence } from "./FeedbackPanel";
import ListeningPracticeView from "./ListeningPracticeView";

export default function PracticeSession() {
  const id = Number(useParams().attemptId);
  const attempt = useQuery({
    queryKey: ["attempt", id],
    queryFn: () => api<Attempt>(`/attempts/${id}`),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  if (attempt.isPending) return <p className="center">Loading…</p>;
  if (attempt.error) return <p className="center error">{attempt.error.message}</p>;
  if (attempt.data.status === "completed") return <Navigate to={`/report/${id}`} replace />;
  if (attempt.data.sections[0].skill === "writing") return <Navigate to={`/exam/${id}`} replace />; // the exam's writing screen, untimed
  return <Session attempt={attempt.data} section={attempt.data.sections[0]} />;
}

function Session({ attempt, section }: { attempt: Attempt; section: AttemptSection }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const r = useResponses(attempt, section);
  const parts = section.parts!;
  const [feedback, setFeedback] = useState<Feedback[]>(section.feedback);
  const partOf = (qid: number) => parts.findIndex((p) => p.groups.some((g) => g.questions.some((q) => q.id === qid)));
  const [partIndex, setPartIndex] = useState(() => Math.max(0, partOf(r.current)));
  const part = parts[partIndex];
  const [showTranscript, setShowTranscript] = useState(false);
  const showInTranscript = (qid: number) => {
    setShowTranscript(true);
    requestAnimationFrame(() => requestAnimationFrame(() => showEvidence(qid))); // after the transcript renders
  };
  const url = `/attempts/${attempt.id}/sections/${section.id}`;
  const trainer = attempt.mode === "trainer";

  const check = useMutation({
    mutationFn: async (groupId: number) => {
      await r.save(); // the server marks what it has, so send the latest answers first
      return api<Feedback[]>(`/practice/sessions/${attempt.id}/check-group`, { method: "POST", body: { group_id: groupId } });
    },
    onSuccess: (results) => setFeedback((f) => [...f, ...results]),
  });
  const finish = useMutation({
    mutationFn: async () => {
      await r.save();
      return api<Attempt>(`${url}/submit`, { method: "POST" });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["attempts"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/report/${attempt.id}`, { replace: true });
    },
  });

  const groups = parts.flatMap((p) => p.groups);
  const checked = new Set(feedback.map((f) => f.group_id));
  const unchecked = groups.filter((g) => !checked.has(g.id)).length;
  const confirmFinish = () => {
    const msg = unchecked
      ? `${unchecked} group${unchecked > 1 ? "s are" : " is"} not checked yet; they will be marked as they are. Finish?`
      : "Finish this session and see the summary?";
    if (window.confirm(msg)) finish.mutate();
  };
  const goPart = (i: number) => {
    setPartIndex(i);
    r.setCurrent(parts[i].groups[0].questions[0].id);
  };

  const results = Object.fromEntries(feedback.map((f) => [f.question_id, f.is_correct]));
  const evidence = feedback.map((f) => ({ qid: f.question_id, ...f.evidence }));
  const title = [...new Set(groups.map((g) => qtypeLabel(g.qtype)))].join(", ");

  return (
    <div className="exam practice">
      <header className="examhead">
        <span>
          <strong>{trainer ? "Trainer" : "Practice"}</strong> <span className="muted">{title}</span>
        </span>
        <Elapsed since={section.started_at!} offset={r.clockOffset} />
        <span className="tools">
          <button onClick={() => r.save().then(() => navigate(trainer ? "/trainer" : "/practice"))}>Leave</button>
          <button className="primary" disabled={finish.isPending} onClick={confirmFinish}>
            Finish
          </button>
        </span>
      </header>

      {parts.length > 1 && (
        <div className="partbar">
          <button aria-label="Previous passage" disabled={partIndex === 0} onClick={() => goPart(partIndex - 1)}>
            ◀
          </button>
          <strong>
            {part.audio ? "Recording" : "Passage"} {partIndex + 1} of {parts.length}
          </strong>
          <button aria-label="Next passage" disabled={partIndex === parts.length - 1} onClick={() => goPart(partIndex + 1)}>
            ▶
          </button>
        </div>
      )}

      {(() => {
        const questions = part.groups.map((g) => {
          const done = checked.has(g.id);
          const answered = g.questions.some((q) => isAnswered(r.answers[q.id]));
          return (
            <div key={g.id}>
              <QuestionGroup
                group={g}
                answers={r.answers}
                setAnswer={r.setAnswer}
                current={r.current}
                focus={r.setCurrent}
                locked={done}
                results={results}
              />
              {done ? (
                <FeedbackPanel
                  results={feedback.filter((f) => f.group_id === g.id)}
                  {...(part.audio ? { onShow: showInTranscript, where: "transcript" as const } : {})}
                />
              ) : (
                <p className="checkrow">
                  <button className="primary" disabled={!answered || check.isPending} onClick={() => check.mutate(g.id)}>
                    Check answers
                  </button>
                  {!answered && <span className="muted"> Answer at least one question first.</span>}
                </p>
              )}
            </div>
          );
        });
        const body = (
          <>
            {questions}
            {check.error && <p className="error">{check.error.message}</p>}
          </>
        );
        return part.audio ? (
          <ListeningPracticeView
            key={part.number}
            part={part}
            evidence={evidence}
            showTranscript={showTranscript}
            setShowTranscript={setShowTranscript}
          >
            {body}
          </ListeningPracticeView>
        ) : (
          <ReadingView key={part.number} part={part} highlights={r.highlights} setHighlights={r.setHighlights} evidence={evidence}>
            {body}
          </ReadingView>
        );
      })()}
      {finish.error && <p className="toast error">{finish.error.message}</p>}
    </div>
  );
}

/** Practice has no limit, but seeing the time helps you pace yourself. */
function Elapsed({ since, offset }: { since: string; offset: { current: number } }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);
  const s = Math.max(0, Math.floor((Date.now() + offset.current - Date.parse(since)) / 1000));
  return (
    <span className="elapsed" aria-label="Time since you started">
      {Math.floor(s / 60)}:{String(s % 60).padStart(2, "0")}
    </span>
  );
}
