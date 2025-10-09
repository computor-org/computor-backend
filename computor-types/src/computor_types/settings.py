from pydantic import BaseModel
from enum import Enum
# gitlab api
# project ->
#   mr_default_target_self (default=true, false waere upstream)
#   merge_method (default=rebase_merge, merge, ff)
#   only_allow_merge_if_pipeline_succeeds (default=true)
#   only_allow_merge_if_all_discussions_are_resolved (default=true)

class MergeMethod(str, Enum):
    RebaseMerge = 'rebase_merge'
    Merge = 'merge'
    FastForward = 'ff'
    
class StudentTemplateSettings(BaseModel):
    mr_default_target_self: bool = True
    merge_method: MergeMethod = MergeMethod.RebaseMerge
    only_allow_merge_if_pipeline_succeeds: bool = True
    only_allow_merge_if_all_discussions_are_resolved: bool = True
    
sts = StudentTemplateSettings()