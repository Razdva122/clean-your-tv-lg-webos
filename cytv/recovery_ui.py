"""Shared bounded recovery wording for desktop and Android; never authority."""

REMOVAL_STAGES = {
    'requested':'Removal has been requested.',
    'original-writers-fenced':'Previous setup work is stopped.',
    'controls-restored':'TV controls are restored.',
    'package-removal':'Removing Clean Your TV packages…',
    'private-cleanup':'Removing private setup data…',
    # A saved terminal stage is historical until the adapter checks current state.
    'verified-clean':'Verifying removal…',
}
REMOVAL_BLOCKERS = {
    'removal-requested':'',
    'original-writer-active':'Previous setup work may still be running. Keep recovery data and continue only through recovery.',
    'ownership-conflict':'Cleanup ownership could not be verified. Keep recovery data.',
    'controls-unverified':'TV controls could not be verified. Keep LG Home active and save the report.',
    'removal-terminal-unknown':'A package removal result is unknown. It will not be repeated.',
    'private-cleanup-incomplete':'Private setup data cleanup is incomplete. Keep recovery data.',
    'removal-verified':'',
}


def removal_details(plan):
    if plan.get('disposition') != 'clean-removal' or type(plan.get('removal')) is not dict:
        return {}
    value = plan['removal']
    stage = value.get('stage') if type(value.get('stage')) is str else None
    reason = value.get('reason') if type(value.get('reason')) is str else None
    return {'stage_text':REMOVAL_STAGES.get(stage, 'Verifying removal…'),
            'blocker_text':REMOVAL_BLOCKERS.get(reason,
                'Removal is not verified. Recovery data was kept.')}
