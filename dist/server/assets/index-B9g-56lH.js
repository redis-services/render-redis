import { jsxs, jsx, Fragment } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Globe, Github, Linkedin, Mail, X, Menu, Zap, KeyRound, Database, ShieldCheck, LayoutDashboard, RefreshCw } from "lucide-react";
const navLinks = [
  { label: "Features", href: "#features" },
  { label: "Architecture", href: "#architecture" },
  { label: "Roadmap", href: "#roadmap" },
  { label: "Waitlist", href: "#waitlist" }
];
const socials = [
  { icon: Globe, href: "https://www.mohammadramiz.in", label: "Portfolio" },
  { icon: Github, href: "https://github.com/RamizMohammad", label: "GitHub" },
  { icon: Linkedin, href: "https://www.linkedin.com/in/ramizmohammad", label: "LinkedIn" },
  { icon: Mail, href: "mailto:ramizanas6@gmail.com", label: "Email" }
];
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return /* @__PURE__ */ jsxs(
    "nav",
    {
      className: `fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? "bg-background/80 backdrop-blur-xl border-b border-border shadow-lg shadow-black/10" : "bg-transparent"}`,
      children: [
        /* @__PURE__ */ jsxs("div", { className: "max-w-6xl mx-auto px-6 h-16 flex items-center justify-between", children: [
          /* @__PURE__ */ jsxs("a", { href: "#", className: "flex items-center gap-2 group", children: [
            /* @__PURE__ */ jsx("img", { src: "/logo.jpeg", alt: "Central Redis Logo", className: "h-8 w-auto hover:scale-110 transition-transform" }),
            /* @__PURE__ */ jsx("span", { className: "font-bold text-foreground tracking-tight", children: "Central Redis" })
          ] }),
          /* @__PURE__ */ jsxs("div", { className: "hidden md:flex items-center gap-6", children: [
            navLinks.map((link) => /* @__PURE__ */ jsx(
              "a",
              {
                href: link.href,
                className: "text-sm text-muted-foreground hover:text-foreground transition-colors",
                children: link.label
              },
              link.href
            )),
            /* @__PURE__ */ jsx("div", { className: "w-px h-5 bg-border mx-1" }),
            socials.map((s) => /* @__PURE__ */ jsx(
              "a",
              {
                href: s.href,
                target: "_blank",
                rel: "noopener noreferrer",
                "aria-label": s.label,
                className: "text-muted-foreground hover:text-redis transition-colors",
                children: /* @__PURE__ */ jsx(s.icon, { className: "w-4 h-4" })
              },
              s.label
            ))
          ] }),
          /* @__PURE__ */ jsx(
            "button",
            {
              onClick: () => setMobileOpen(!mobileOpen),
              className: "md:hidden text-muted-foreground hover:text-foreground transition-colors",
              "aria-label": "Toggle menu",
              children: mobileOpen ? /* @__PURE__ */ jsx(X, { className: "w-5 h-5" }) : /* @__PURE__ */ jsx(Menu, { className: "w-5 h-5" })
            }
          )
        ] }),
        /* @__PURE__ */ jsx(AnimatePresence, { children: mobileOpen && /* @__PURE__ */ jsx(
          motion.div,
          {
            initial: { opacity: 0, height: 0 },
            animate: { opacity: 1, height: "auto" },
            exit: { opacity: 0, height: 0 },
            className: "md:hidden bg-background/95 backdrop-blur-xl border-b border-border overflow-hidden",
            children: /* @__PURE__ */ jsxs("div", { className: "px-6 py-4 flex flex-col gap-3", children: [
              navLinks.map((link) => /* @__PURE__ */ jsx(
                "a",
                {
                  href: link.href,
                  onClick: () => setMobileOpen(false),
                  className: "text-sm text-muted-foreground hover:text-foreground transition-colors py-1",
                  children: link.label
                },
                link.href
              )),
              /* @__PURE__ */ jsx("div", { className: "h-px bg-border my-1" }),
              /* @__PURE__ */ jsx("div", { className: "flex items-center gap-4", children: socials.map((s) => /* @__PURE__ */ jsx(
                "a",
                {
                  href: s.href,
                  target: "_blank",
                  rel: "noopener noreferrer",
                  "aria-label": s.label,
                  className: "text-muted-foreground hover:text-redis transition-colors",
                  children: /* @__PURE__ */ jsx(s.icon, { className: "w-4 h-4" })
                },
                s.label
              )) })
            ] })
          }
        ) })
      ]
    }
  );
}
function HeroSection() {
  return /* @__PURE__ */ jsxs("section", { className: "relative min-h-screen flex items-center justify-center overflow-hidden", children: [
    /* @__PURE__ */ jsx("div", { className: "absolute inset-0 bg-grid opacity-30" }),
    /* @__PURE__ */ jsx("div", { className: "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-gradient-radial opacity-20 pointer-events-none" }),
    /* @__PURE__ */ jsxs("div", { className: "relative z-10 max-w-4xl mx-auto px-6 text-center", children: [
      /* @__PURE__ */ jsx(
        motion.div,
        {
          initial: { opacity: 0, y: 20 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6 },
          children: /* @__PURE__ */ jsxs("div", { className: "inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full border border-border bg-surface text-sm text-muted-foreground", children: [
            /* @__PURE__ */ jsx("span", { className: "w-2 h-2 rounded-full bg-redis animate-pulse" }),
            "Currently in private use — public access coming soon"
          ] })
        }
      ),
      /* @__PURE__ */ jsxs(
        motion.h1,
        {
          className: "text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.05]",
          initial: { opacity: 0, y: 30 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.7, delay: 0.1 },
          children: [
            "One Redis layer.",
            /* @__PURE__ */ jsx("br", {}),
            /* @__PURE__ */ jsx("span", { className: "text-gradient-redis", children: "Every project." })
          ]
        }
      ),
      /* @__PURE__ */ jsx(
        motion.p,
        {
          className: "mt-6 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed",
          initial: { opacity: 0, y: 20 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6, delay: 0.3 },
          children: "Central Redis is a multi-tenant Redis API platform. Isolated storage, per-project API keys, and a clean admin layer — without managing Redis infrastructure for every build."
        }
      ),
      /* @__PURE__ */ jsxs(
        motion.div,
        {
          className: "mt-10 flex flex-col sm:flex-row items-center justify-center gap-4",
          initial: { opacity: 0, y: 20 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6, delay: 0.45 },
          children: [
            /* @__PURE__ */ jsx(
              "a",
              {
                href: "#waitlist",
                className: "px-8 py-3.5 rounded-lg bg-redis text-redis-foreground font-semibold text-sm tracking-wide glow-redis-sm transition-all hover:brightness-110 hover:scale-[1.02]",
                children: "Request Early Access"
              }
            ),
            /* @__PURE__ */ jsx(
              "a",
              {
                href: "#features",
                className: "px-8 py-3.5 rounded-lg border border-border text-foreground font-medium text-sm transition-colors hover:bg-surface",
                children: "See How It Works"
              }
            )
          ]
        }
      ),
      /* @__PURE__ */ jsx(
        motion.div,
        {
          className: "mt-16 max-w-xl mx-auto",
          initial: { opacity: 0, y: 30 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.7, delay: 0.6 },
          children: /* @__PURE__ */ jsxs("div", { className: "rounded-xl border border-border bg-surface overflow-hidden text-left", children: [
            /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2 px-4 py-3 border-b border-border", children: [
              /* @__PURE__ */ jsx("div", { className: "w-3 h-3 rounded-full bg-redis/30" }),
              /* @__PURE__ */ jsx("div", { className: "w-3 h-3 rounded-full bg-muted" }),
              /* @__PURE__ */ jsx("div", { className: "w-3 h-3 rounded-full bg-muted" }),
              /* @__PURE__ */ jsx("span", { className: "ml-2 text-xs text-muted-foreground font-mono-code", children: "API Request" })
            ] }),
            /* @__PURE__ */ jsx("pre", { className: "p-5 text-sm leading-relaxed font-mono-code overflow-x-auto", children: /* @__PURE__ */ jsxs("code", { children: [
              /* @__PURE__ */ jsx("span", { className: "text-muted-foreground", children: "POST" }),
              " ",
              /* @__PURE__ */ jsx("span", { className: "text-redis", children: "/api/set" }),
              "\n",
              /* @__PURE__ */ jsx("span", { className: "text-muted-foreground", children: "X-API-Key:" }),
              " ",
              /* @__PURE__ */ jsx("span", { className: "text-foreground/60", children: "proj_sk_abc123..." }),
              "\n\n",
              /* @__PURE__ */ jsx("span", { className: "text-muted-foreground", children: "{" }),
              "\n",
              "  ",
              /* @__PURE__ */ jsx("span", { className: "text-redis", children: '"key"' }),
              ": ",
              /* @__PURE__ */ jsx("span", { className: "text-foreground/70", children: '"session:user:42"' }),
              ",",
              "\n",
              "  ",
              /* @__PURE__ */ jsx("span", { className: "text-redis", children: '"value"' }),
              ": ",
              /* @__PURE__ */ jsx("span", { className: "text-foreground/70", children: '"active"' }),
              ",",
              "\n",
              "  ",
              /* @__PURE__ */ jsx("span", { className: "text-redis", children: '"ttl"' }),
              ": ",
              /* @__PURE__ */ jsx("span", { className: "text-foreground/70", children: "3600" }),
              "\n",
              /* @__PURE__ */ jsx("span", { className: "text-muted-foreground", children: "}" })
            ] }) })
          ] })
        }
      )
    ] })
  ] });
}
const capabilities = [
  {
    title: "Multi-Tenant by Default",
    description: "Every project gets its own isolated namespace. Keys never collide. Data never leaks."
  },
  {
    title: "One API, Full Redis Power",
    description: "GET, SET, DELETE, TTL, increment, lists, hashes, key listing, flush — all through a single REST API."
  },
  {
    title: "Per-Project API Keys",
    description: "Each project authenticates independently. Rotate keys, manage access, control everything."
  },
  {
    title: "Admin Dashboard",
    description: "See all projects, manage configs, and monitor usage from a single control plane."
  }
];
function WhatItDoesSection() {
  return /* @__PURE__ */ jsx("section", { id: "features", className: "py-32 px-6", children: /* @__PURE__ */ jsxs("div", { className: "max-w-5xl mx-auto", children: [
    /* @__PURE__ */ jsxs(
      motion.div,
      {
        className: "text-center mb-16",
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true },
        transition: { duration: 0.5 },
        children: [
          /* @__PURE__ */ jsx("p", { className: "text-sm font-semibold uppercase tracking-widest text-redis mb-3", children: "What It Does" }),
          /* @__PURE__ */ jsx("h2", { className: "text-3xl md:text-4xl font-bold tracking-tight", children: "Redis infrastructure, abstracted" }),
          /* @__PURE__ */ jsx("p", { className: "mt-4 text-muted-foreground max-w-2xl mx-auto", children: "Central Redis gives you everything you need to use Redis across multiple projects — without provisioning, configuring, or babysitting a single instance." })
        ]
      }
    ),
    /* @__PURE__ */ jsx("div", { className: "grid md:grid-cols-2 gap-6", children: capabilities.map((item, i) => /* @__PURE__ */ jsxs(
      motion.div,
      {
        className: "group p-6 rounded-xl border border-border bg-surface hover:border-redis/30 transition-colors",
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true },
        transition: { duration: 0.4, delay: i * 0.1 },
        children: [
          /* @__PURE__ */ jsx("h3", { className: "text-lg font-semibold mb-2 group-hover:text-redis transition-colors", children: item.title }),
          /* @__PURE__ */ jsx("p", { className: "text-sm text-muted-foreground leading-relaxed", children: item.description })
        ]
      },
      item.title
    )) })
  ] }) });
}
const features = [
  {
    icon: Zap,
    title: "Blazing Fast",
    description: "Redis-backed, sub-millisecond reads. No cold starts, no connection pooling headaches."
  },
  {
    icon: KeyRound,
    title: "Per-Project Keys",
    description: "Every project authenticates with its own API key. Full isolation, zero crosstalk."
  },
  {
    icon: Database,
    title: "Rich Data Types",
    description: "Strings, lists, hashes, counters, TTLs — all the Redis primitives you need, via REST."
  },
  {
    icon: ShieldCheck,
    title: "Namespace Isolation",
    description: "Projects can't see each other's data. Namespacing is enforced at the platform level."
  },
  {
    icon: LayoutDashboard,
    title: "Admin Dashboard",
    description: "Create projects, rotate keys, flush data, and view operations — all from one panel."
  },
  {
    icon: RefreshCw,
    title: "Keep-Alive Built In",
    description: "Deployment-stable with built-in keep-alive. No dropped connections on serverless hosts."
  }
];
function FeatureGridSection() {
  return /* @__PURE__ */ jsx("section", { id: "features", className: "py-32 px-6 border-t border-border", children: /* @__PURE__ */ jsxs("div", { className: "max-w-5xl mx-auto", children: [
    /* @__PURE__ */ jsxs(
      motion.div,
      {
        className: "text-center mb-16",
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true },
        transition: { duration: 0.5 },
        children: [
          /* @__PURE__ */ jsx("p", { className: "text-sm font-semibold uppercase tracking-widest text-redis mb-3", children: "Features" }),
          /* @__PURE__ */ jsx("h2", { className: "text-3xl md:text-4xl font-bold tracking-tight", children: "Developer-first, by design" })
        ]
      }
    ),
    /* @__PURE__ */ jsx("div", { className: "grid sm:grid-cols-2 lg:grid-cols-3 gap-6", children: features.map((f, i) => /* @__PURE__ */ jsxs(
      motion.div,
      {
        className: "group p-6 rounded-xl border border-border bg-surface hover:border-redis/20 transition-colors",
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true },
        transition: { duration: 0.35, delay: i * 0.07 },
        children: [
          /* @__PURE__ */ jsx("div", { className: "mb-4 w-10 h-10 rounded-lg bg-redis/10 flex items-center justify-center group-hover:bg-redis/20 transition-colors", children: /* @__PURE__ */ jsx(f.icon, { className: "w-5 h-5 text-redis" }) }),
          /* @__PURE__ */ jsx("h3", { className: "font-semibold mb-1.5", children: f.title }),
          /* @__PURE__ */ jsx("p", { className: "text-sm text-muted-foreground leading-relaxed", children: f.description })
        ]
      },
      f.title
    )) })
  ] }) });
}
function FounderSection() {
  return /* @__PURE__ */ jsx("section", { className: "py-32 px-6 border-t border-border", children: /* @__PURE__ */ jsx("div", { className: "max-w-3xl mx-auto", children: /* @__PURE__ */ jsxs(
    motion.div,
    {
      initial: { opacity: 0, y: 20 },
      whileInView: { opacity: 1, y: 0 },
      viewport: { once: true },
      transition: { duration: 0.6 },
      children: [
        /* @__PURE__ */ jsx("p", { className: "text-sm font-semibold uppercase tracking-widest text-redis mb-6", children: "Why I Built It" }),
        /* @__PURE__ */ jsx("blockquote", { className: "text-xl md:text-2xl font-medium leading-relaxed text-foreground/90", children: '"I kept spinning up Redis for every side project. Same patterns, same configs, same overhead. Central Redis started as a way to stop repeating myself — one API that handles namespaced storage across all my builds."' }),
        /* @__PURE__ */ jsxs("div", { className: "mt-8 flex items-center gap-4", children: [
          /* @__PURE__ */ jsx("div", { className: "w-10 h-10 rounded-full bg-redis/20 flex items-center justify-center text-redis font-bold text-sm", children: "CR" }),
          /* @__PURE__ */ jsxs("div", { children: [
            /* @__PURE__ */ jsx("p", { className: "text-sm font-semibold", children: "Builder & Founder" }),
            /* @__PURE__ */ jsx("p", { className: "text-xs text-muted-foreground", children: "Currently in private use — built for real workloads" })
          ] })
        ] })
      ]
    }
  ) }) });
}
const steps = [
  {
    num: "01",
    title: "Create a Project",
    description: "Spin up a new project in the admin dashboard. Instantly get an isolated namespace and API key."
  },
  {
    num: "02",
    title: "Hit the API",
    description: "Use simple REST endpoints for any Redis operation — GET, SET, lists, hashes, TTL, and more."
  },
  {
    num: "03",
    title: "Scale Without Thinking",
    description: "All projects share one managed Redis layer. No provisioning, no config drift, no maintenance."
  }
];
function ArchitectureSection() {
  return /* @__PURE__ */ jsxs("section", { id: "architecture", className: "py-32 px-6 border-t border-border relative overflow-hidden", children: [
    /* @__PURE__ */ jsx("div", { className: "absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-radial opacity-10 pointer-events-none" }),
    /* @__PURE__ */ jsxs("div", { className: "max-w-5xl mx-auto relative z-10", children: [
      /* @__PURE__ */ jsxs(
        motion.div,
        {
          className: "text-center mb-16",
          initial: { opacity: 0, y: 20 },
          whileInView: { opacity: 1, y: 0 },
          viewport: { once: true },
          transition: { duration: 0.5 },
          children: [
            /* @__PURE__ */ jsx("p", { className: "text-sm font-semibold uppercase tracking-widest text-redis mb-3", children: "How It Works" }),
            /* @__PURE__ */ jsx("h2", { className: "text-3xl md:text-4xl font-bold tracking-tight", children: "Three steps. Zero ops." })
          ]
        }
      ),
      /* @__PURE__ */ jsx("div", { className: "grid md:grid-cols-3 gap-8", children: steps.map((step, i) => /* @__PURE__ */ jsxs(
        motion.div,
        {
          className: "relative",
          initial: { opacity: 0, y: 20 },
          whileInView: { opacity: 1, y: 0 },
          viewport: { once: true },
          transition: { duration: 0.4, delay: i * 0.15 },
          children: [
            /* @__PURE__ */ jsx("span", { className: "text-5xl font-bold text-redis/15 font-mono-code", children: step.num }),
            /* @__PURE__ */ jsx("h3", { className: "text-lg font-semibold mt-2 mb-2", children: step.title }),
            /* @__PURE__ */ jsx("p", { className: "text-sm text-muted-foreground leading-relaxed", children: step.description })
          ]
        },
        step.num
      )) }),
      /* @__PURE__ */ jsx(
        motion.div,
        {
          className: "mt-20 flex flex-wrap items-center justify-center gap-3",
          initial: { opacity: 0 },
          whileInView: { opacity: 1 },
          viewport: { once: true },
          transition: { duration: 0.6, delay: 0.3 },
          children: ["FastAPI", "Redis", "MongoDB Atlas", "REST API", "Namespaced Storage"].map((tech) => /* @__PURE__ */ jsx(
            "span",
            {
              className: "px-4 py-1.5 text-xs font-mono-code rounded-full border border-border text-muted-foreground bg-surface",
              children: tech
            },
            tech
          ))
        }
      )
    ] })
  ] });
}
const roadmapItems = [
  { label: "Now", title: "Private internal use", description: "Battle-tested on real projects. Stable API. Admin dashboard live.", active: true },
  { label: "Next", title: "Public API & onboarding", description: "Self-serve project creation, usage-based billing, and developer docs.", active: false },
  { label: "Later", title: "SDKs, webhooks & more", description: "Client libraries, event hooks, pub/sub, and extended data structures.", active: false }
];
function RoadmapSection() {
  return /* @__PURE__ */ jsx("section", { id: "roadmap", className: "py-32 px-6 border-t border-border", children: /* @__PURE__ */ jsxs("div", { className: "max-w-4xl mx-auto", children: [
    /* @__PURE__ */ jsxs(
      motion.div,
      {
        className: "text-center mb-16",
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true },
        transition: { duration: 0.5 },
        children: [
          /* @__PURE__ */ jsx("p", { className: "text-sm font-semibold uppercase tracking-widest text-redis mb-3", children: "Roadmap" }),
          /* @__PURE__ */ jsx("h2", { className: "text-3xl md:text-4xl font-bold tracking-tight", children: "Built for now. Growing for later." }),
          /* @__PURE__ */ jsx("p", { className: "mt-4 text-muted-foreground max-w-xl mx-auto", children: "Central Redis runs in production today. The goal is to open it up — carefully, deliberately — when the foundation is rock solid." })
        ]
      }
    ),
    /* @__PURE__ */ jsx("div", { className: "space-y-6", children: roadmapItems.map((item, i) => /* @__PURE__ */ jsxs(
      motion.div,
      {
        className: `flex gap-6 p-6 rounded-xl border transition-colors ${item.active ? "border-redis/40 bg-redis/5" : "border-border bg-surface"}`,
        initial: { opacity: 0, x: -20 },
        whileInView: { opacity: 1, x: 0 },
        viewport: { once: true },
        transition: { duration: 0.4, delay: i * 0.1 },
        children: [
          /* @__PURE__ */ jsx("div", { className: "flex-shrink-0", children: /* @__PURE__ */ jsx(
            "span",
            {
              className: `inline-block px-3 py-1 text-xs font-semibold rounded-full ${item.active ? "bg-redis text-redis-foreground" : "bg-muted text-muted-foreground"}`,
              children: item.label
            }
          ) }),
          /* @__PURE__ */ jsxs("div", { children: [
            /* @__PURE__ */ jsx("h3", { className: "font-semibold mb-1", children: item.title }),
            /* @__PURE__ */ jsx("p", { className: "text-sm text-muted-foreground", children: item.description })
          ] })
        ]
      },
      item.label
    )) })
  ] }) });
}
function FooterSection() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const handleSubmit = (e) => {
    e.preventDefault();
    if (email.trim()) {
      setSubmitted(true);
    }
  };
  return /* @__PURE__ */ jsxs("section", { id: "waitlist", className: "py-32 px-6 border-t border-border relative overflow-hidden", children: [
    /* @__PURE__ */ jsx("div", { className: "absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-gradient-radial opacity-15 pointer-events-none" }),
    /* @__PURE__ */ jsx("div", { className: "max-w-2xl mx-auto text-center relative z-10", children: /* @__PURE__ */ jsx(
      motion.div,
      {
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true },
        transition: { duration: 0.6 },
        children: submitted ? /* @__PURE__ */ jsxs(
          motion.div,
          {
            initial: { opacity: 0, scale: 0.9 },
            animate: { opacity: 1, scale: 1 },
            transition: { duration: 0.4 },
            children: [
              /* @__PURE__ */ jsx("div", { className: "text-4xl mb-4", children: "🎉" }),
              /* @__PURE__ */ jsx("h2", { className: "text-3xl md:text-4xl font-bold tracking-tight", children: "You're on the list!" }),
              /* @__PURE__ */ jsx("p", { className: "mt-4 text-muted-foreground", children: "Thanks for signing up. We'll notify you as soon as early access opens." })
            ]
          }
        ) : /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("h2", { className: "text-3xl md:text-4xl font-bold tracking-tight", children: "Get on the list." }),
          /* @__PURE__ */ jsx("p", { className: "mt-4 text-muted-foreground", children: "Central Redis is currently invite-only. Drop your email to be first in line when we open up access." }),
          /* @__PURE__ */ jsxs(
            "form",
            {
              onSubmit: handleSubmit,
              className: "mt-8 flex flex-col sm:flex-row gap-3 max-w-md mx-auto",
              children: [
                /* @__PURE__ */ jsx(
                  "input",
                  {
                    type: "email",
                    required: true,
                    value: email,
                    onChange: (e) => setEmail(e.target.value),
                    placeholder: "you@example.com",
                    className: "flex-1 px-4 py-3 rounded-lg bg-surface border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-redis/50 transition-shadow"
                  }
                ),
                /* @__PURE__ */ jsx(
                  "button",
                  {
                    type: "submit",
                    className: "px-6 py-3 rounded-lg bg-redis text-redis-foreground font-semibold text-sm tracking-wide glow-redis-sm transition-all hover:brightness-110 hover:scale-[1.02] whitespace-nowrap",
                    children: "Request Access"
                  }
                )
              ]
            }
          ),
          /* @__PURE__ */ jsx("p", { className: "mt-4 text-xs text-muted-foreground", children: "No spam. Just a heads-up when it's your turn." })
        ] })
      }
    ) }),
    /* @__PURE__ */ jsxs("div", { className: "mt-24 pt-8 border-t border-border max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6 text-xs text-muted-foreground", children: [
      /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsx("span", { className: "w-2 h-2 rounded-full bg-redis" }),
        /* @__PURE__ */ jsx("span", { className: "font-semibold text-foreground", children: "Central Redis" })
      ] }),
      /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-4", children: [
        /* @__PURE__ */ jsx("a", { href: "https://www.mohammadramiz.in", target: "_blank", rel: "noopener noreferrer", className: "hover:text-foreground transition-colors", children: "Portfolio" }),
        /* @__PURE__ */ jsx("a", { href: "https://github.com/RamizMohammad", target: "_blank", rel: "noopener noreferrer", className: "hover:text-foreground transition-colors", children: "GitHub" }),
        /* @__PURE__ */ jsx("a", { href: "https://www.linkedin.com/in/ramizmohammad", target: "_blank", rel: "noopener noreferrer", className: "hover:text-foreground transition-colors", children: "LinkedIn" }),
        /* @__PURE__ */ jsx("a", { href: "mailto:ramizanas6@gmail.com", className: "hover:text-foreground transition-colors", children: "Contact" })
      ] }),
      /* @__PURE__ */ jsxs("p", { children: [
        "© ",
        (/* @__PURE__ */ new Date()).getFullYear(),
        " Central Redis. Built with intent."
      ] })
    ] })
  ] });
}
function Index() {
  return /* @__PURE__ */ jsxs(Fragment, { children: [
    /* @__PURE__ */ jsx(Navbar, {}),
    /* @__PURE__ */ jsxs("main", { className: "pt-16", children: [
      /* @__PURE__ */ jsx(HeroSection, {}),
      /* @__PURE__ */ jsx(WhatItDoesSection, {}),
      /* @__PURE__ */ jsx(FeatureGridSection, {}),
      /* @__PURE__ */ jsx(FounderSection, {}),
      /* @__PURE__ */ jsx(ArchitectureSection, {}),
      /* @__PURE__ */ jsx(RoadmapSection, {}),
      /* @__PURE__ */ jsx(FooterSection, {})
    ] })
  ] });
}
export {
  Index as component
};
