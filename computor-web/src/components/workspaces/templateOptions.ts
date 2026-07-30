import type {
  CoderTemplate,
  TemplatePreparation,
} from '@/src/types/workspaces';
import { templateTaskStage, type TemplateTaskStage } from './templateTaskStage';

/**
 * One workspace type as a user meets it, and whether they can have it.
 *
 * The three places a user picks a workspace type — the workspaces page, a
 * course page, a course card — used to each decide availability their own way,
 * which is how a course ended up offering `bash-workspace` as a button whose
 * only effect was a 503 snackbar. Availability is decided here, once, from the
 * two things the templates endpoint reports: what Coder has, and what is being
 * deployed right now.
 */
export type TemplateAvailability =
  /** Ready to use. May still carry a `stage` — an update leaves the current
      version running, so it stays selectable while the new one builds. */
  | 'available'
  /** Being deployed and not usable yet. `stage` says how far it has got. */
  | 'preparing'
  /** Its deployment failed. Not usable, and it will not fix itself. */
  | 'failed'
  /** Coder does not have it and nothing is building it. */
  | 'unavailable';

export interface TemplateOption {
  name: string;
  display_name?: string | null;
  description?: string | null;
  icon?: string | null;
  availability: TemplateAvailability;
  /** Something a bar can draw, when a deployment is running or has failed. */
  stage?: TemplateTaskStage;
  /** Why it cannot be picked — the disabled card's hover text. */
  reason?: string;
}

export function isUsable(option: TemplateOption): boolean {
  return option.availability === 'available';
}

/** Display name if the template has one, else its raw Coder name. */
export function templateLabel(option: {
  display_name?: string | null;
  name: string;
}): string {
  return option.display_name || option.name;
}

function byLabel(a: TemplateOption, b: TemplateOption): number {
  return templateLabel(a).localeCompare(templateLabel(b));
}

/**
 * The workspace types a user may pick, from one `GET /coder/templates`.
 *
 * `templates` is what Coder has and the user is allowed to use; `preparing` is
 * what an administrator is deploying, scoped the same way. A template can be in
 * both — a re-push of something already live — and that case stays usable.
 */
export function buildTemplateOptions(
  templates: CoderTemplate[],
  preparing: TemplatePreparation[] = [],
): TemplateOption[] {
  const preparingByName = new Map(preparing.map((entry) => [entry.name, entry]));
  const liveNames = new Set(templates.map((template) => template.name));

  const options: TemplateOption[] = templates.map((template) => {
    const running = preparingByName.get(template.name);
    return {
      name: template.name,
      display_name: template.display_name,
      description: template.description,
      icon: template.icon,
      availability: 'available',
      // An update to something live: worth showing, never worth blocking on.
      // The card keeps working; the bar just says a new version is coming.
      stage: running ? templateTaskStage(running, running.task_name) : undefined,
    };
  });

  for (const entry of preparing) {
    if (liveNames.has(entry.name)) continue; // folded into the live card above
    const stage = templateTaskStage(entry, entry.task_name);
    const failed = entry.status === 'failed';
    options.push({
      name: entry.name,
      display_name: entry.display_name,
      description: entry.description,
      icon: entry.icon,
      availability: failed ? 'failed' : 'preparing',
      stage,
      reason: failed
        ? `${stage.label} — this workspace type is not available. Contact your administrator.`
        : `${templateLabel(entry)} is being prepared (${stage.label.toLowerCase()}) and cannot be used yet.`,
    });
  }

  return options.sort(byLabel);
}

/**
 * A type a course allows that the templates listing does not offer.
 *
 * Course templates are chosen by name and stay chosen: the template can be
 * removed from Coder, or never deployed at all, long after a course asked for
 * it. Such a type still belongs on the page — it is what the course expects
 * students to use — but as something visibly out of reach rather than a button
 * that fails on click.
 */
export function unavailableOption(template: {
  template_name: string;
  display_name?: string | null;
  description?: string | null;
  icon?: string | null;
}): TemplateOption {
  return {
    name: template.template_name,
    display_name: template.display_name,
    description: template.description,
    icon: template.icon,
    availability: 'unavailable',
    reason:
      'This workspace type has not been set up on this server yet. ' +
      'Contact your administrator.',
  };
}

/**
 * What a course offers, crossed with what the server actually has.
 *
 * A course picks its types by name and keeps them; the templates listing is
 * the only thing that knows whether one of those names is live, building, or
 * gone. When the listing could not be consulted at all (the compact course
 * card does not fetch it, and a listing can 403), the course settings' own
 * `exists_in_coder` is the fallback — weaker, since it cannot tell "building"
 * from "never deployed", but enough to stop offering a click that only ever
 * produced "Template … is not yet available".
 */
export function courseTemplateOption(
  item: {
    template_name: string;
    display_name?: string | null;
    description?: string | null;
    icon?: string | null;
    exists_in_coder?: boolean | null;
  },
  option: TemplateOption | undefined,
  listingAnswered: boolean,
): TemplateOption {
  if (option) {
    return {
      ...option,
      display_name: option.display_name ?? item.display_name,
      description: option.description ?? item.description,
      icon: option.icon ?? item.icon,
    };
  }
  // Known-missing: either the listing answered and does not have it, or the
  // course settings say Coder does not. (`exists_in_coder` is null when Coder
  // was unreachable — nothing is claimed then, and the click speaks for it.)
  if (listingAnswered || item.exists_in_coder === false) {
    return unavailableOption(item);
  }
  return {
    name: item.template_name,
    display_name: item.display_name,
    description: item.description,
    icon: item.icon,
    availability: 'available',
  };
}

/** Short state word for a card's second line. */
export function availabilityLabel(option: TemplateOption): string {
  if (option.availability === 'available') return '';
  if (option.stage) return option.stage.label;
  return option.availability === 'failed' ? 'Not available' : 'Not set up yet';
}
