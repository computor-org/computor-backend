// The name to show for a person, from whatever the API sent about them.
//
// Three pages had grown their own `memberName`: the lecturer member table, the
// lecturer workspace table, and now the group tree. They disagreed on the last
// resort — one printed `user_id`, the other the string "Unknown" — so the same
// nameless account read as a UUID on one page and as a word on the next.
//
// "Unknown" wins, for the reason `graderName` already states: a raw UUID is not
// a name. It is neither recognisable nor typeable, and printing one where a name
// belongs looks like a bug rather than like missing data.

/** Just the name-bearing fields, so this accepts `UserList`, a nested `user`, and test doubles. */
export interface NameableUser {
  given_name?: string | null;
  family_name?: string | null;
  email?: string | null;
}

/** Given + family name, else the email, else `fallback`. Never an id. */
export function userName(user?: NameableUser | null, fallback = 'Unknown'): string {
  const name = [user?.given_name, user?.family_name]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(' ');
  return name || user?.email?.trim() || fallback;
}

/** The same, for a record that carries its user nested — a course member. */
export function memberName(
  member?: { user?: NameableUser | null } | null,
  fallback = 'Unknown',
): string {
  return userName(member?.user, fallback);
}
