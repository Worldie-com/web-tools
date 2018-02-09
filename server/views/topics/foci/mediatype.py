import logging
from flask import jsonify, request
import flask_login
from server.cache import cache
from server import app
from server.util.request import api_error_handler, json_error_response, form_fields_required, arguments_required
from server.views.topics.apicache import topic_story_count
from server.auth import user_mediacloud_key, user_mediacloud_client
from server.views.topics.apicache import topic_tag_coverage, _cached_topic_tag_counts, cached_topic_timespan_list
from server.views.topics.foci import FOCAL_TECHNIQUE_BOOLEAN_QUERY
from server.util.tags import cached_tags_in_tag_set, media_with_tag, TAG_SETS_ID_MEDIA_TYPE
import json
logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_SIZE = 5000
@app.route('/api/topics/<topics_id>/focal-sets/media-type/preview/story-counts', methods=['GET'])
@flask_login.login_required
@api_error_handler
def media_type_story_counts(topics_id):
    tag_story_counts = []
    media_type_tags = cached_media_tags(TAG_SETS_ID_MEDIA_TYPE)
    # grab the total stories
    total_stories = topic_story_count(user_mediacloud_key(), topics_id)['count']
    # make a count for each tag based on media_id
    for tag in media_type_tags:
    
        # media_ids_query_clause = "media_id:({})".format(tag_media_ids)
        query_clause = "tags_id_media:{}".format(tag['tags_id'])
        if len(tag['media_ids']) > 0:
            tagged_story_count = topic_story_count(user_mediacloud_key(), topics_id, q=query_clause)['count']
        else:
            tagged_story_count = 0
        tag_story_counts.append({
            'label': tag['label'],
            'tags_id': tag['tags_id'],
            'count': tagged_story_count,
            'pct': float(tagged_story_count)/float(total_stories)
        })

    return jsonify({'story_counts': tag_story_counts})


@app.route('/api/topics/<topics_id>/focal-sets/media-type/preview/coverage', methods=['GET'])
@flask_login.login_required
@api_error_handler
def media_type_coverage(topics_id):
    media_type_tags = cached_media_tags(TAG_SETS_ID_MEDIA_TYPE)
    # grab the total stories
    total_stories = topic_story_count(user_mediacloud_key(), topics_id)['count']
    # count the stories in any media in tagged as media_type
    tag_media_ids = " ".join(str(tag['tags_id']) for tag in media_type_tags)
    query_clause = "tags_id_media:({})".format(tag_media_ids)
    tagged_story_count = topic_story_count(user_mediacloud_key(), topics_id, q=query_clause)['count']
    return jsonify({'counts': {'count': tagged_story_count, 'total': total_stories}})

@cache
def cached_media_tags(tag_sets_id):
    media_type_tags = cached_tags_in_tag_set(tag_sets_id)
    return media_type_tags

@app.route('/api/topics/<topics_id>/focal-sets/media-type/create', methods=['POST'])
@form_fields_required('focalSetName', 'focalSetDescription')
@flask_login.login_required
def create_media_type_focal_set(topics_id):
    user_mc = user_mediacloud_client()
    # grab the focalSetName and focalSetDescription and then make one
    focal_set_name = request.form['focalSetName']
    focal_set_description = request.form['focalSetDescription']
    media_type_tags = cached_media_tags(TAG_SETS_ID_MEDIA_TYPE)
    focal_technique = FOCAL_TECHNIQUE_BOOLEAN_QUERY
    new_focal_set = user_mc.topicFocalSetDefinitionCreate(topics_id, focal_set_name, focal_set_description, focal_technique)
    if 'focal_set_definitions_id' not in new_focal_set:
        return json_error_response('Unable to create the subtopic set')
    # now make the foci in it - one for each media type
    focus_def_results = []
    for tag in media_type_tags:
        params = {
            'name': tag['label'],
            'description': u"Stories from {} sources".format(tag['label']),
            'query': "tags_id_media:{}".format(tag['tags_id']),
            'focal_set_definitions_id': new_focal_set['focal_set_definitions_id'],
        }
        result = user_mc.topicFocusDefinitionCreate(topics_id, **params)
        focus_def_results.append(result)
    return {'success': True}
