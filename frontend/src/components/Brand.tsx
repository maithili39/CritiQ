import { Link } from "react-router-dom";

type BrandProps = {
  size?: "sm" | "md";
  to?: string;
};

export default function Brand({ size = "md", to = "/" }: BrandProps) {
  const textSize = size === "sm" ? "text-[24px]" : "text-[30px]";
  const sparkSize = size === "sm" ? "w-4 h-4" : "w-5 h-5";

  return (
    <Link to={to} className="brand inline-flex items-center gap-0.5">
      <span className={`brand-word ${textSize}`}>
        Criti<span className="brand-q">Q</span>
      </span>
      <svg className={`brand-spark ${sparkSize}`} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2c.6 3.4 1.4 5.6 2.6 6.9 1.2 1.3 3.3 2.1 6.4 2.6-3.1.5-5.2 1.3-6.4 2.6-1.2 1.3-2 3.5-2.6 6.9-.6-3.4-1.4-5.6-2.6-6.9-1.2-1.3-3.3-2.1-6.4-2.6 3.1-.5 5.2-1.3 6.4-2.6C10.6 7.6 11.4 5.4 12 2z" />
      </svg>
    </Link>
  );
}
