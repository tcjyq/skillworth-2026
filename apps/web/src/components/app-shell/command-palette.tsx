"use client";

import { useRouter } from "next/navigation";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from "@/components/ui/command";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { allRoutes, primaryRoutes, secondaryRoutes } from "./routes";

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();
  const go = (href: string) => { router.push(href); onOpenChange(false); };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent showCloseButton={false} className="top-1/3 max-w-[640px] translate-y-0 overflow-hidden rounded-[4px] border border-[#303331] p-0 shadow-[0_24px_80px_rgba(0,0,0,.6)]">
        <DialogHeader className="sr-only"><DialogTitle>SkillWorth 命令面板</DialogTitle><DialogDescription>搜索页面和功能</DialogDescription></DialogHeader>
        <Command className="rounded-[4px]">
          <CommandInput placeholder="搜索市场、技能、岗位或工具…" />
          <CommandList>
            <CommandEmpty>没有找到匹配项。</CommandEmpty>
            <CommandGroup heading="核心分析">{primaryRoutes.map(({ href, label, icon: Icon }) => <CommandItem key={href} value={label} onSelect={() => go(href)}><Icon size={16} />{label}</CommandItem>)}</CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="数据与决策">{secondaryRoutes.map(({ href, label, icon: Icon }) => <CommandItem key={href} value={label} onSelect={() => go(href)}><Icon size={16} />{label}</CommandItem>)}</CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}

export const commandRouteCount = allRoutes.length;
