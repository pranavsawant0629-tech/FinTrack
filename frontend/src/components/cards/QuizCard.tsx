import React, { useState } from "react";
import { Award, CheckCircle2, XCircle, HelpCircle, ArrowRight, Loader2 } from "lucide-react";
import { apiClient } from "../../api/client";

interface QuizCardProps {
  data: Record<string, any>;
  userId?: string;
}

export const QuizCard: React.FC<QuizCardProps> = ({ data, userId }) => {
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [gradedResult, setGradedResult] = useState<any>(data.graded_items ? data : null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // If already graded
  if (gradedResult && (gradedResult.graded_items || gradedResult.results)) {
    const items = gradedResult.graded_items || gradedResult.results || [];
    const scorePct = gradedResult.score_percentage ?? gradedResult.percentage ?? 0;
    const correctCount = gradedResult.correct_count ?? gradedResult.score ?? 0;
    const totalCount = gradedResult.total_questions ?? gradedResult.total ?? items.length;

    return (
      <div className="bg-surface border border-border-warm rounded-xl p-4 sm:p-5 shadow-xs my-3 animate-in fade-in duration-150">
        <div className="flex items-center justify-between border-b border-border-warm/60 pb-2.5 mb-3.5">
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-marigold" />
            <h4 className="font-serif font-semibold text-ivory text-sm tracking-tight">
              Quiz Evaluation Results
            </h4>
          </div>
          <div className="text-right">
            <span className="text-xs font-mono font-bold text-marigold bg-marigold/15 px-2.5 py-0.5 rounded border border-marigold/30">
              {correctCount} / {totalCount} ({scorePct.toFixed(0)}%)
            </span>
          </div>
        </div>

        <div className="space-y-3">
          {items.map((item: any, idx: number) => {
            const isCorrect = item.is_correct;
            return (
              <div
                key={item.question_id || idx}
                className={`p-3.5 rounded-lg border text-xs ${
                  isCorrect
                    ? "bg-teal/15 border-teal/35 text-ivory"
                    : "bg-terracotta/15 border-terracotta/35 text-ivory"
                }`}
              >
                <div className="flex items-start gap-2 mb-2">
                  {isCorrect ? (
                    <CheckCircle2 className="w-4 h-4 text-teal shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-4 h-4 text-terracotta shrink-0 mt-0.5" />
                  )}
                  <p className="font-serif font-medium text-ivory text-xs sm:text-sm">{item.question_text || item.question}</p>
                </div>

                <div className="grid grid-cols-2 gap-2 my-2 font-mono text-[11px]">
                  <div className="bg-elevated p-2 rounded border border-border-warm/60">
                    <span className="text-muted-warm block text-[10px] font-sans">Your Answer</span>
                    <span className={isCorrect ? "text-teal font-bold" : "text-terracotta font-bold"}>
                      Option {item.selected_option}
                    </span>
                  </div>
                  {!isCorrect && (
                    <div className="bg-elevated p-2 rounded border border-border-warm/60">
                      <span className="text-muted-warm block text-[10px] font-sans">Correct Answer</span>
                      <span className="text-teal font-bold">Option {item.correct_option}</span>
                    </div>
                  )}
                </div>

                {item.explanation && (
                  <p className="text-[11px] text-muted-warm mt-2 bg-surface p-2.5 rounded border border-border-warm/60 leading-relaxed font-sans">
                    <span className="font-semibold text-ivory">Explanation: </span>
                    {item.explanation}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Active quiz questions
  const questions: any[] = data.questions || (data.question ? [data] : []);
  if (questions.length === 0) return null;

  const handleSelect = (qId: string, optKey: string) => {
    setSelectedAnswers((prev) => ({ ...prev, [qId]: optKey }));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const submissions = Object.entries(selectedAnswers).map(([question_id, selected_option]) => ({
        question_id,
        selected_option,
      }));
      const res = await apiClient.submitQuiz(submissions, userId);
      setGradedResult(res);
    } catch (err: any) {
      setSubmitError(err.message || "Failed to submit quiz.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const allAnswered = questions.every((q) => selectedAnswers[q.id]);

  return (
    <div className="bg-surface border border-border-warm rounded-xl p-4 sm:p-5 shadow-xs my-3 animate-in fade-in duration-150">
      <div className="flex items-center justify-between border-b border-border-warm/60 pb-2.5 mb-3.5">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-marigold" />
          <h4 className="font-serif font-semibold text-ivory text-sm tracking-tight">
            Financial Knowledge Check
          </h4>
        </div>
        <span className="text-[10px] text-marigold font-mono bg-marigold/15 px-2 py-0.5 rounded border border-marigold/30 font-medium">
          {questions.length} {questions.length === 1 ? "Question" : "Questions"}
        </span>
      </div>

      <div className="space-y-4">
        {questions.map((q, idx) => {
          const selected = selectedAnswers[q.id];
          const options: Record<string, string> = q.options || {};

          return (
            <div key={q.id || idx} className="p-3.5 bg-elevated rounded-xl border border-border-warm">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 bg-surface border border-border-warm rounded text-muted-warm">
                  {q.topic || "General"}
                </span>
                <span className="text-[10px] capitalize font-mono text-teal">
                  {q.difficulty || "standard"}
                </span>
              </div>

              <p className="text-xs sm:text-sm font-serif font-medium text-ivory mb-3 leading-snug">
                {idx + 1}. {q.question || q.question_text}
              </p>

              <div className="space-y-2">
                {Object.entries(options).map(([optKey, optVal]) => {
                  const isChecked = selected === optKey;
                  return (
                    <button
                      key={optKey}
                      type="button"
                      onClick={() => handleSelect(q.id, optKey)}
                      className={`w-full text-left p-2.5 rounded-lg text-xs transition-all duration-150 flex items-start gap-2.5 border cursor-pointer ${
                        isChecked
                          ? "bg-marigold/15 border-marigold text-ivory"
                          : "bg-surface border-border-warm/60 text-ivory/80 hover:bg-elevated hover:border-border-warm"
                      }`}
                    >
                      <span
                        className={`font-mono text-[11px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                          isChecked ? "bg-marigold text-espresso" : "bg-elevated border border-border-warm text-muted-warm"
                        }`}
                      >
                        {optKey}
                      </span>
                      <span className="leading-relaxed font-sans">{optVal}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {submitError && (
        <p className="text-xs text-terracotta mt-2 bg-terracotta/15 p-2 rounded border border-terracotta/30 font-sans">
          {submitError}
        </p>
      )}

      <div className="mt-4 pt-3 border-t border-border-warm/60 flex justify-end">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!allAnswered || isSubmitting}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-150 ${
            allAnswered && !isSubmitting
              ? "bg-marigold text-espresso hover:bg-marigold-hover shadow-xs cursor-pointer active:scale-95"
              : "bg-elevated border border-border-warm text-muted-warm/40 cursor-not-allowed"
          }`}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Grading...</span>
            </>
          ) : (
            <>
              <span>Submit Answers</span>
              <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
