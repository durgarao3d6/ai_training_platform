import { Notice } from "@/components/ui/primitives";

/** Shows every message from a failed save. Renders nothing when there are none. */
export function ErrorList({ errors }: { errors: string[] }) {
  if (!errors.length) return null;
  return (
    <Notice>
      {errors.length === 1 ? (
        <p>{errors[0]}</p>
      ) : (
        <ul>
          {errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
    </Notice>
  );
}
