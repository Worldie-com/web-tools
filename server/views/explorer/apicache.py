from server import mc, TOOL_API_KEY
from server.cache import cache, key_generator
from server.auth import user_mediacloud_client, user_mediacloud_key, is_user_logged_in
from server.util.tags import processed_by_cliff_query_clause
import server.util.wordembeddings as wordembeddings


def sentence_count(q, start_date_str=None, end_date_str=None):
    return cached_sentence_count(q, start_date_str, end_date_str)


@cache.cache_on_arguments(function_key_generator=key_generator)
def cached_sentence_count(q, start_date_str=None, end_date_str=None):
    sentence_count_result = mc.sentenceCount(solr_query=q, split_start_date=start_date_str,
                                             split_end_date=end_date_str, split=True)
    return sentence_count_result


def sentence_list(q, rows=10):
    # can't cache by api key here because we need to use tool mc to get sentences
    return _cached_sentence_list(q, rows)


@cache.cache_on_arguments(function_key_generator=key_generator)
def _cached_sentence_list(q, rows):
    return mc.sentenceList(solr_query=q, rows=rows)


def top_tags_with_coverage(q, tag_sets_id, limit, sample_size):
    tag_counts = most_used_tags(q, tag_sets_id, limit, sample_size)
    coverage = cliff_coverage(q)
    for t in tag_counts:  # add in pct of what's been run through CLIFF to total results
        t['pct'] = float(t['count']) / sample_size
    coverage['results'] = tag_counts
    return coverage


def most_used_tags(q, tag_sets_id, limit, sample_size):
    # top tags used in stories matching query (pass in None for no limit)
    api_key = _api_key()
    sentence_count_results = _cached_most_used_tags(api_key, q, tag_sets_id, sample_size)
    top_count_results = sentence_count_results[:limit] if limit is not None else sentence_count_results
    return top_count_results


def cliff_coverage(q):
    # dict of info about stories tagged by CLIFF
    return tag_set_coverage(q, u'({}) AND {}'.format(q, processed_by_cliff_query_clause()))


def tag_set_coverage(total_q, subset_q):
    api_key = _api_key()
    coverage = {
        'totals': _cached_total_story_count(api_key, total_q)['count'],
        'counts': _cached_total_story_count(api_key, subset_q)['count'],
    }
    coverage['coverage_percentage'] = 0 if coverage['totals'] is 0 else float(coverage['counts'])/float(coverage['totals'])
    return coverage


@cache.cache_on_arguments(function_key_generator=key_generator)
def _cached_most_used_tags(api_key, query, tag_sets_id, sample_size):
    # top tags used in stories matching query
    # api_key used for caching at the user level
    local_mc = _mc_client()
    return local_mc.sentenceFieldCount('*', query, field='tags_id_stories', tag_sets_id=tag_sets_id,
                                       sample_size=sample_size)


def story_count(q):
    api_key = _api_key()
    return _cached_total_story_count(api_key, q)


@cache.cache_on_arguments(function_key_generator=key_generator)
def _cached_total_story_count(api_key, q):
    # api_key is included to keep the cache at the user-level
    local_mc = _mc_client()
    count = local_mc.storyCount(q)
    return count


def random_story_list(q, limit):
    return story_list_page(q, stories_per_page=limit, sort=mc.SORT_RANDOM)


def story_list_page(q, last_processed_stories_id=None, stories_per_page=1000, sort=mc.SORT_PROCESSED_STORIES_ID):
    api_key = _api_key()
    return _cached_story_list_page(api_key, q, last_processed_stories_id, stories_per_page, sort)


@cache.cache_on_arguments(function_key_generator=key_generator)
def _cached_story_list_page(api_key, query, last_processed_stories_id, stories_per_page, sort):
    # be user-specific in this cache to be careful about permissions on stories
    # api_key passed in just to make this a user-level cache
    local_client = _mc_client()
    return local_client.storyList(query, last_processed_stories_id=last_processed_stories_id, rows=stories_per_page,
                                  sort=sort)


def media(media_id):
    api_key = _api_key()
    return _cached_media(api_key, media_id)


@cache.cache_on_arguments(function_key_generator=key_generator)
def _cached_media(api_key, media_id):
    # api_key passed in just to make this a user-level cache
    local_client = _mc_client()
    return local_client.media(media_id)


def word_count(q, ngram_size, num_words, sample_size):
    api_key = _api_key()
    return _cached_word_count(api_key, q, ngram_size, num_words, sample_size)


@cache.cache_on_arguments(function_key_generator=key_generator)
def _cached_word_count(api_key, q, ngram_size, num_words, sample_size):
    local_mc = _mc_client()
    return local_mc.wordCount('*', q, ngram_size=ngram_size, num_words=num_words, sample_size=sample_size)


def word2vec_google_2d(words):
    return _cached_word2vec_google_2d(words)


@cache.cache_on_arguments(function_key_generator=key_generator)
def _cached_word2vec_google_2d(words):
    # don't need to be user-level cache here - can be app-wide because results are from another service that doesn't
    # have any concept of permissioning
    word2vec_results = wordembeddings.google_news_2d(words)
    return word2vec_results


def tag_set(tag_sets_id):
    return _cached_tag_set(_api_key(), tag_sets_id)


@cache.cache_on_arguments(function_key_generator=key_generator)
def _cached_tag_set(api_key, tag_sets_id):
    local_mc = _mc_client()
    return local_mc.tagSet(tag_sets_id)


def _api_key():
    api_key = user_mediacloud_key() if is_user_logged_in() else TOOL_API_KEY
    return api_key


def _mc_client():
    # return the user's client handler, or a tool one if not logged in
    if is_user_logged_in():
        client_to_use = user_mediacloud_client()
    else:
        client_to_use = mc
    return client_to_use
