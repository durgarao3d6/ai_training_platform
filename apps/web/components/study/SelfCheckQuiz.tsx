"use client";

import { useId, useState } from "react";

import { Button } from "@/components/ui/primitives";
import type { QuizQuestion } from "@/lib/types";

import styles from "./study.module.css";

/**
 * Practice questions for the learner. Answers are checked in the browser and never saved or
 * scored: this is self-study, not an assessment (scores only come from the scoring service).
 */
export function SelfCheckQuiz({ questions }: { questions: QuizQuestion[] }) {
  return (
    <>
      <p className={styles.muted}>Practice only. Your answers are not saved or marked.</p>
      {questions.map((q, index) => (
        <Question key={index} index={index} question={q} />
      ))}
    </>
  );
}

function Question({ index, question }: { index: number; question: QuizQuestion }) {
  const name = useId();
  const [choice, setChoice] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const right = checked && choice === question.correct_index;

  return (
    <fieldset className={styles.question}>
      <legend>
        {index + 1}. {question.question}
      </legend>
      {question.options.map((option, i) => (
        <label key={i} className={styles.option}>
          <input
            type="radio"
            name={name}
            checked={choice === i}
            onChange={() => {
              setChoice(i);
              setChecked(false);
            }}
          />
          <span>{option}</span>
        </label>
      ))}
      <div className={styles.option}>
        <Button size="sm" variant="secondary" disabled={choice === null} onClick={() => setChecked(true)}>
          Check answer
        </Button>
      </div>
      <div aria-live="polite">
        {checked && (
          <p className={right ? styles.feedbackRight : styles.feedbackWrong}>
            {right ? "Correct. " : `Not quite. The answer is “${question.options[question.correct_index]}”. `}
            {question.explanation}
          </p>
        )}
      </div>
    </fieldset>
  );
}
