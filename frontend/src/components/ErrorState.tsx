export function ErrorState({ message }: { message: string }) {
  return <p className="state error">{message}</p>;
}
