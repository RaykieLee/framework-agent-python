"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useKnowledgeBases } from "@/hooks";
import type { KBScope } from "@/types";
import { useTranslations } from "next-intl";

interface CreateKBDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (id: string) => void;
}

export function CreateKBDialog({ open, onOpenChange, onCreated }: CreateKBDialogProps) {
  const t = useTranslations("knowledgeBases");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [scope, setScope] = useState<KBScope>("personal");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { createKB } = useKnowledgeBases();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    const kb = await createKB({
      name: name.trim(),
      description: description.trim() || undefined,
      scope,
    });
    setIsSubmitting(false);
    if (kb) {
      setName("");
      setDescription("");
      setScope("personal");
      onOpenChange(false);
      onCreated?.(kb.id);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("createTitle")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label={t("nameLabel")} htmlFor="kb-name">
            <Input
              id="kb-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("namePlaceholder")}
              autoFocus
            />
          </FormField>
          <FormField label={t("descriptionLabel")} htmlFor="kb-description">
            <Textarea
              id="kb-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("descriptionPlaceholder")}
              rows={2}
            />
          </FormField>
          <div className="space-y-1.5">
            <Label htmlFor="kb-scope">{t("scopeLabel")}</Label>
            <Select value={scope} onValueChange={(v) => setScope(v as KBScope)}>
              <SelectTrigger id="kb-scope">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="personal">{t("scopePersonal")}</SelectItem>
                <SelectItem value="org">{t("scopeOrganization")}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={!name.trim() || isSubmitting}>
              {isSubmitting ? t("creating") : t("create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
