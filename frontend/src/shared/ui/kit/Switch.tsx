import * as S from "@radix-ui/react-switch";

export function Switch({ checked, onChange, label }: { checked: boolean; onChange(v: boolean): void; label: string }) {
  return (<label className="kswitch"><S.Root className="kswitch-root" checked={checked} onCheckedChange={onChange}><S.Thumb className="kswitch-thumb" /></S.Root><span>{label}</span></label>);
}
