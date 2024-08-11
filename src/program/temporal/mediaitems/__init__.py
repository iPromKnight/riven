from .media_item_activities import handle_requested_or_unknown_state, handle_indexed_or_partially_completed_state, \
    handle_scraped_state, handle_downloaded_state, handle_symlinked_state, handle_completed_state, store_item  # noqa
from .media_item_workflow import MediaItemWorkflow  # noqa


def media_item_activities() -> []:
    return [
        handle_requested_or_unknown_state,
        handle_indexed_or_partially_completed_state,
        handle_scraped_state,
        handle_downloaded_state,
        handle_symlinked_state,
        handle_completed_state, store_item
    ]