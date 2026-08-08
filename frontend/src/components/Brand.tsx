import { Link } from "react-router-dom";

type BrandProps = {
  size?: "sm" | "md";
  to?: string;
};

export default function Brand({ size = "md", to = "/" }: BrandProps) {
  const textSize = size === "sm" ? "text-[24px]" : "text-[30px]";

  return (
    <Link to={to} className="brand inline-flex items-center gap-0.5">
      <span className={`brand-word ${textSize}`}>
        Criti<span className="brand-q">Q</span>
      </span>
      <span className="brand-dot" aria-hidden="true" />
    </Link>
  );
}
