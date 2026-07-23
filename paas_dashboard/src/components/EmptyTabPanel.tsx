import {
  Activity,
  AppWindow,
  Box,
  ChartPie,
  Code,
  Database,
  FileClock,
  GitBranch,
  Plug,
  Network,
  Plus,
  Rocket,
  SquareTerminal,
  Variable,
} from "lucide-react";
import "./EmptyTabPanel.css";

interface ToolItem {
  icon: React.ReactNode;
  title: string;
  description: string;
  action: "preview" | "editor" | "scalar" | null;
}

interface Section {
  title: string;
  description: string;
  items: ToolItem[];
}

interface EmptyTabPanelProps {
  onOpenPreview: () => void;
  onOpenEditor: () => void;
  onOpenScalar: () => void;
}

const sections: Section[] = [
  {
    title: "开发工具",
    description: "提供代码编辑、实时预览与调试能力，支持全流程的开发与版本管理",
    items: [
      {
        icon: <AppWindow size={20} />,
        title: "预览",
        description: "实时预览运行效果，并进行代码调试",
        action: "preview",
      },
      {
        icon: <Code size={20} />,
        title: "编辑器",
        description: "浏览、编写和修改项目的源代码文件",
        action: "editor",
      },
      {
        icon: <SquareTerminal size={20} />,
        title: "终端",
        description: "访问系统命令行，执行脚本或安装依赖包",
        action: null,
      },
      {
        icon: <GitBranch size={20} />,
        title: "版本控制",
        description: "管理代码版本，查看具体的代码变更差异和提交记录",
        action: null,
      },
      {
        icon: <Network size={20} />,
        title: "API 客户端",
        description: "基于 Scalar 的交互式 API 请求调试客户端",
        action: "scalar",
      },
    ],
  },
  {
    title: "集成服务",
    description: "快速配置数据库、身份验证及存储等后端设施，为应用赋予底层能力",
    items: [
      {
        icon: <Plug size={20} />,
        title: "集成管理",
        description: "配置项目所需的模型能力、外部 API 及各类后端服务资源",
        action: null,
      },
      {
        icon: <Variable size={20} />,
        title: "环境变量",
        description: "安全存储 API Key 等配置信息",
        action: null,
      },
      {
        icon: <Database size={20} />,
        title: "数据库",
        description: "查看和管理项目中的结构化数据",
        action: null,
      },
      {
        icon: <Box size={20} />,
        title: "对象存储",
        description: "存储图片、视频、文档等非结构化文件资源",
        action: null,
      },
    ],
  },
  {
    title: "托管",
    description: "一键将应用发布至生产环境，并提供实时的数据监控与日志排查服务",
    items: [
      {
        icon: <Rocket size={20} />,
        title: "部署",
        description: "项目一站式部署上线，托管至火山引擎",
        action: null,
      },
      {
        icon: <ChartPie size={20} />,
        title: "数据分析",
        description: "监控访问流量与性能指标",
        action: null,
      },
      {
        icon: <FileClock size={20} />,
        title: "日志",
        description: "查看生产环境运行记录日志",
        action: null,
      },
      {
        icon: <Activity size={20} />,
        title: "用量管理",
        description: "查看和管理项目的积分预算",
        action: null,
      },
    ],
  },
];

function ToolCard({
  item,
  onOpenPreview,
  onOpenEditor,
  onOpenScalar,
}: {
  item: ToolItem;
  onOpenPreview: () => void;
  onOpenEditor: () => void;
  onOpenScalar: () => void;
}) {
  const isImplemented = item.action !== null;

  const handleClick = () => {
    if (item.action === "preview") {
      onOpenPreview();
    } else if (item.action === "editor") {
      onOpenEditor();
    } else if (item.action === "scalar") {
      onOpenScalar();
    }
  };

  return (
    <div className="empty-tab__card">
      <div className="empty-tab__card-left">
        <div className="empty-tab__icon">{item.icon}</div>
        <div className="empty-tab__text">
          <div className="empty-tab__card-title">{item.title}</div>
          <div className="empty-tab__card-desc">{item.description}</div>
        </div>
      </div>
      <button
        className={`empty-tab__add-btn${
          !isImplemented ? " empty-tab__add-btn--disabled" : ""
        }`}
        aria-label={`添加 ${item.title}`}
        onClick={handleClick}
        disabled={!isImplemented}
      >
        <Plus size={18} />
      </button>
    </div>
  );
}

export function EmptyTabPanel({ onOpenPreview, onOpenEditor, onOpenScalar }: EmptyTabPanelProps) {
  return (
    <div className="empty-tab__panel">
      <div className="empty-tab__content">
        {sections.map((section) => (
          <section key={section.title} className="empty-tab__section">
            <h2 className="empty-tab__section-title">{section.title}</h2>
            <p className="empty-tab__section-desc">{section.description}</p>
            <div className="empty-tab__card-grid">
              {section.items.map((item) => (
                <ToolCard
                  key={item.title}
                  item={item}
                  onOpenPreview={onOpenPreview}
                  onOpenEditor={onOpenEditor}
                  onOpenScalar={onOpenScalar}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
