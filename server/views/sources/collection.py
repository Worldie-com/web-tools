import logging
from flask import jsonify, request
import flask_login
from operator import itemgetter
from mediacloud.tags import MediaTag, TAG_ACTION_ADD, TAG_ACTION_REMOVE
from werkzeug import secure_filename
import csv as pycsv
import server.util.csv as csv
import os
from server.views.sources import COLLECTIONS_TAG_SET_ID, TAG_SETS_ID_PUBLICATION_COUNTRY,  \
    COLLECTIONS_TEMPLATE_PROPS_CREATE, COLLECTIONS_TEMPLATE_PROPS_VIEW, COLLECTIONS_TEMPLATE_PROPS_EDIT, \
    isMetaDataTagSet, POPULAR_COLLECTION_LIST, FEATURED_COLLECTION_LIST

from server import app, mc, db
from server.util.request import arguments_required, form_fields_required, api_error_handler
from server.cache import cache
from server.auth import user_mediacloud_key, user_mediacloud_client, user_name
from server.views.sources.words import cached_wordcount, stream_wordcount_csv
from server.views.sources.geocount import stream_geo_csv, cached_geotag_count
from server.views.sources.sentences import cached_recent_sentence_counts, stream_sentence_count_csv
from server.views.sources.metadata import _cached_tags_in_tag_set
from server.views.sources.favorites import _add_user_favorite_flag_to_collections, _add_user_favorite_flag_to_sources

logger = logging.getLogger(__name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['csv']


@app.route('/api/collections/uploadSourceListFromTemplate', methods=['POST'])
def upload_file():
    logger.debug("inside upload");
    logger.debug("request is %s", request.method)
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return jsonify({'status': 'Error', 'message': 'No file part'})
        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return jsonify({'status': 'Error', 'message': 'No selected file'})
        if file and allowed_file(file.filename):
            props = COLLECTIONS_TEMPLATE_PROPS_EDIT
            filename = secure_filename(file.filename)
            # have to save b/c otherwise we can't locate the file path (security restriction)... can delete afterwards
            file.save(os.path.join('', filename))
            with open(file.filename, 'rU') as f:
                reader = pycsv.DictReader(f)
                reader.fieldnames = props
                newSources = []
                updatedOnly = []
                results = []
                newWithMetaAndEmpties = []
                reader.next()  # this means we have to have a header
                for line in reader:
                    try:
                        newline = []
                        has_media_id = False
                        # python 2.7 csv module doesn't support unicode so have to do the decode/encode here for cleaned up vals
                        for item in line.items():
                            if item[0] == 'pub_country' and item[1] not in ['', None]:
                                # don't decode unless there is something in there
                                line['pub_country'] = item[1].decode('utf-8', errors='replace').encode('ascii',
                                                                                                       errors='ignore')
                            if item[0] == 'media_id' and item[1] not in ['', None]:
                                has_media_id = True

                        if has_media_id:
                                # remove all empty fields b/c we don't want to overwrite any fields with empty, just to update with values
                                # eg metadata, public_notes, editor_notes
                                # then decode. Not sure this is working
                            temp = {k: v for k, v in line.items() if v not in ['', None] }
                            decoded = {k.decode('utf-8', errors='replace').encode('ascii', errors='ignore').lower(): v for
                                   k, v in temp.items()}
                            updatedOnly.append(decoded)
                            # don't add it to the create/newline stack
                            continue

                        # add to newline all items in line except for media_id b/c MC will create
                        newline = {k: v for k, v in line.items() if k not in ['', None] and k.lower() != 'media_id'}

                        # decode all keys as long as there is a key (why?)
                        newline = {k.decode('utf-8', errors='replace').encode('ascii', errors='ignore').lower(): v for
                                   k, v in line.items() if k not in ['', None] }

                        # store metadata in another list(currently ignoring other fields whose values may be empty such as public_notes etc)
                        newWithMetaAndEmpties.append(newline)

                        newlineNoEmpties = {k: v for k, v in newWithMetaAndEmpties.items() if v != ''}
                        # remove metadata from primary list b/c mediaCreate will not add them 
                        noEmptiesNoMeta = {k: v for k, v in newlineNoEmpties.items() if k != 'pub_country'}
                        newSources.append(noEmptiesNoMeta)
                        
                    except Exception as e:
                        logger.error("Couldn't process a CSV row: " + str(e))
                        return jsonify({'status': 'Error', 'message': "couldn't process a CSV row: " + str(e)})

                if len(newSources) > 100:
                    return jsonify({'status': 'Error', 'message': 'Too many sources to upload. The limit is 100.'})
                else:
                    if len(newSources) > 0:

                        results.append(crud_source_from_template(newSources, newWithMetaAndEmpties, True))
                    if len(updatedOnly) > 0:
                        logger.debug("$$$$$$$$$$$$$$$$")
                        logger.debug('updating sources')
                        results.append(crud_source_from_template(updatedOnly, newWithMetaAndEmpties, False))
                    return jsonify({'results':results})

    return jsonify({'status': 'Error', 'message': 'Something went wrong. Check your CSV file for formatting errors'})


def crud_source_from_template(sourceList, newOrUpdatedWithMetaAndEmpties, createNew):
    user_mc = user_mediacloud_client()
    result = []
    if (createNew):
        result = user_mc.mediaUpdateWithDict(sourceList)
    else:
        for src in sourceList:
            result.append(user_mc.mediaUpdate(src))

    logger.debug("@@@@@@@@@@@@@@@@@@@@@@")
    logger.debug("success creating or updating source %s", result)
    # status, media_id, url, error in result

    mList = []
    for eachdict in result:
        mNewDictList = [hasEmptiesDict for hasEmptiesDict in newOrUpdatedWithMetaAndEmpties if
                        hasEmptiesDict['url'] == eachdict['url']]
        mList += mNewDictList

    for eachNewDict in mList:
        for eachdict in result:
            missingItems = {k: v for k, v in eachdict.items() if eachNewDict['url'] == eachdict['url']}
            if eachNewDict['url'] == eachdict['url']:
                eachNewDict.update(missingItems)

    # now add/replace metadata to created or updated source
    return updateMetaDataForSources(mList)

# this only adds/replaces metadata with values (does not remove)
def updateMetaDataForSources(sourceList):
    tagISOs = _cached_tags_in_tag_set(TAG_SETS_ID_PUBLICATION_COUNTRY)
    for source in sourceList:
        if source['status'] != 'error':
            metadata_tag_id = source['pub_country'] if source['pub_country'] else None
            if metadata_tag_id not in ['', None]:
                matching = [t for t in tagISOs if t['tag'] == 'pub_' + metadata_tag_id]
                if matching and matching not in ['', None]:
                    metadata_tag_id = matching[0]['tags_id']
                    logger.debug('found metadata to add %s', metadata_tag_id)
                    user_mc.tagMedia(
                        tags=[MediaTag(source['media_id'], tags_id=metadata_tag_id, action=TAG_ACTION_ADD)],
                        clear_others=True)  # make sure to clear any other values set in this metadata tag set
                    logger.debug("success adding metadata")
    # with the results, combine ids with metadata tag list

    # return newly created or updated source list with media_ids filled in
    return sourceList


@app.route('/api/collections/<collection_id>/metadatacoverage.csv')
@flask_login.login_required
@api_error_handler
def api_metadata_download(collection_id):
    user_mc = user_mediacloud_client()
    info = user_mc.tag(collection_id)
    all_media = collection_media_list(user_mediacloud_key(), collection_id)

    metadataItems = []
    for eachDict in all_media:
        for eachItem in eachDict['media_source_tags']:
            if isMetaDataTagSet(eachItem['tag_sets_id']):
                found = False
                for dictItem in metadataItems:
                    if dictItem['metadataId'] == eachItem['tag_sets_id']:
                        temp = dictItem['tagged']
                        dictItem.update({'tagged': temp + 1})
                        found = True
                if not found:
                    metadataItems.append(
                        {'metadataCoverage': eachItem['tag_set'], 'metadataId': eachItem['tag_sets_id'], 'tagged': 1})

    for i in metadataItems:
        temp = len(all_media) - i['tagged']
        i.update({'notTagged': temp})

    props = ['metadataCoverage', 'tagged', 'notTagged']
    filename = "metadataCoverageForCollection" + collection_id + ".csv"
    return csv.stream_response(metadataItems, props, filename)


@app.route('/api/collections/set/<tag_sets_id>', methods=['GET'])
@flask_login.login_required
@api_error_handler
def api_collection_set(tag_sets_id):
    user_mc = user_mediacloud_client()
    info = _cached_collection_set_list(user_mediacloud_key(), tag_sets_id)
    _add_user_favorite_flag_to_collections(info)
    return jsonify(info)


@cache
def _cached_collection_set_list(user_mc_key, tag_sets_id):
    user_mc = user_mediacloud_client()
    tag_set = user_mc.tagSet(tag_sets_id)
    # page through tags
    more_tags = True
    all_tags = []
    last_tags_id = 0
    while more_tags:
        tags = user_mc.tagList(tag_sets_id=tag_set['tag_sets_id'], last_tags_id=last_tags_id, rows=100,
                               public_only=True)
        all_tags = all_tags + tags
        if len(tags) > 0:
            last_tags_id = tags[-1]['tags_id']
        more_tags = len(tags) != 0
    collection_list = all_tags
    collection_list = sorted(collection_list, key=itemgetter('label'))
    return {
        'name': tag_set['label'],
        'description': tag_set['description'],
        'collections': collection_list
    }


# seems that this should have a better name- it's getting a list of sources given a list of collections...
@app.route('/api/collections/list', methods=['GET'])
@arguments_required('coll[]')
@flask_login.login_required
@api_error_handler
def api_collections_by_ids():
    collIdArray = request.args['coll[]'].split(',')
    sources_list = []
    for tagsId in collIdArray:
        info = {}
        all_media = collection_media_list(user_mediacloud_key(), tagsId)
        info = [{'media_id': m['media_id'], 'name': m['name'], 'url': m['url'], 'public_notes':m['public_notes']} for m in all_media]
        _add_user_favorite_flag_to_sources(info)
        sources_list += info;
    return jsonify({'results': sources_list})


@app.route('/api/collections/featured', methods=['GET'])
@flask_login.login_required
@api_error_handler
def api_featured_collections():
    featured_collections = []
    for tagsId in FEATURED_COLLECTION_LIST:
        info = {}
        user_mc = user_mediacloud_client()
        info = user_mc.tag(tagsId)
        info['id'] = tagsId
        info['wordcount']= cached_wordcount(user_mediacloud_key, 'tags_id_media:'+str(tagsId))
        featured_collections += [info];
    return jsonify({'results':featured_collections})

@app.route('/api/collections/popular', methods=['GET'])
@flask_login.login_required
@api_error_handler
def api_popular_collections():
    popular_collections = []
    for tagsId in POPULAR_COLLECTION_LIST:
        info = {}
        user_mc = user_mediacloud_client()
        info = user_mc.tag(tagsId)
        info['id'] = tagsId
        popular_collections += [info];
    return jsonify({'results':popular_collections})

@app.route('/api/collections/<collection_id>/favorite', methods=['PUT'])
@flask_login.login_required
@form_fields_required('favorite')
@api_error_handler
def collection_set_favorited(collection_id):
    favorite = request.form["favorite"]
    username = user_name()
    if int(favorite) == 1:
        db.add_item_to_users_list(username, 'favoriteCollections', int(collection_id))
    else:
        db.remove_item_from_users_list(username, 'favoriteCollections', int(collection_id))
    return jsonify({'isFavorite': favorite})


@app.route('/api/collections/<collection_id>/details')
@flask_login.login_required
@api_error_handler
def api_collection_details(collection_id):
    user_mc = user_mediacloud_client()
    info = user_mc.tag(collection_id)
    _add_user_favorite_flag_to_collections([info])
    info['id'] = collection_id
    info['tag_set'] = _tag_set_info(user_mediacloud_key(), info['tag_sets_id'])
    all_media = collection_media_list(user_mediacloud_key(), collection_id)
    _add_user_favorite_flag_to_sources(all_media)
    info['media'] = all_media

    return jsonify({'results': info})

# either with or without editor notes
@app.route('/api/template/sources.csv')
@flask_login.login_required
@arguments_required('dType')
@api_error_handler
def api_download_sources_template():
    filename = "Collection_Template_for_sources.csv"

    if request.args['dType'] == "1":
        what_type_download = COLLECTIONS_TEMPLATE_PROPS_EDIT
    else:
        what_type_download = COLLECTIONS_TEMPLATE_PROPS_VIEW
    return csv.stream_response(what_type_download, what_type_download, filename)


@app.route('/api/collections/<collection_id>/sources.csv')
@flask_login.login_required
@arguments_required('dType')
@api_error_handler
def api_collection_sources_csv(collection_id):
    user_mc = user_mediacloud_client()
    # info = user_mc.tag(int(collection_id))
    all_media = collection_media_list(user_mediacloud_key(), collection_id)
    for src in all_media:
        for tag in src['media_source_tags']:
            if isMetaDataTagSet(tag['tag_sets_id']):
                src['pub_country'] = tag['tag'][-3:]

        # handle nulls
        if 'pub_country' not in src:
            src['pub_country'] = ''
        if 'editor_notes' not in src:
            src['editor_notes'] = ''
        if 'is_monitored' not in src:
            src['is_monitored'] = ''
        if 'public_notes' not in src:
            src['public_notes'] = ''
        # if from details page, don't include editor_notes
        # src_no_editor_notes = {k: v for k, v in src.items() if k != 'editor_notes'}
    filePrefix = "MC_Downloaded_Template_"

    if request.args['dType'] == "1":
        what_type_download = COLLECTIONS_TEMPLATE_PROPS_EDIT
    else:
        what_type_download = COLLECTIONS_TEMPLATE_PROPS_VIEW
    # if from details page
    # COLLECTIONS_TEMPLATE_PROPS_VIEW vs COLLECTIONS_TEMPLATE_PROPS_EDIT
    return csv.stream_response(all_media, what_type_download, filePrefix, what_type_download)


@app.route('/api/collections/<collection_id>/sources/sentences/count')
@flask_login.login_required
@api_error_handler
def collection_source_sentence_counts(collection_id):
    results = _cached_media_with_sentence_counts(user_mediacloud_key(), collection_id)
    return jsonify({'sources': results})


@app.route('/api/collections/<collection_id>/sources/sentences/count.csv')
@flask_login.login_required
@api_error_handler
def collection_source_sentence_counts_csv(collection_id):
    user_mc = user_mediacloud_client()
    info = user_mc.tag(collection_id)
    results = _cached_media_with_sentence_counts(user_mediacloud_key(), collection_id)
    props = ['media_id', 'name', 'url', 'sentence_count', 'sentence_pct']
    filename = info['label'] + "-source sentence counts.csv"
    return csv.stream_response(results, props, filename)


@cache
def _cached_media_with_sentence_counts(user_mc_key, tag_sets_id):
    sample_size = 2000
    # list all sources first
    sources_by_id = {int(c['media_id']): c for c in collection_media_list(user_mediacloud_key(), tag_sets_id)}
    sentences = mc.sentenceList('*', 'tags_id_media:' + str(tag_sets_id), rows=sample_size, sort=mc.SORT_RANDOM)
    # sum the number of sentences per media source
    sentence_counts = {int(media_id): 0 for media_id in sources_by_id.keys()}
    if 'docs' in sentences['response']:
        for sentence in sentences['response']['docs']:
            if int(sentence['media_id']) in sentence_counts:  # safety check
                sentence_counts[int(sentence['media_id'])] = sentence_counts[int(sentence['media_id'])] + 1.
    # add in sentence count info to media info
    for media_id in sentence_counts.keys():
        sources_by_id[media_id]['sentence_count'] = sentence_counts[media_id]
        sources_by_id[media_id]['sentence_pct'] = sentence_counts[media_id] / sample_size
    return sources_by_id.values()


def _tag_set_info(user_mc_key, tag_sets_id):
    user_mc = user_mediacloud_client()
    return user_mc.tagSet(tag_sets_id)


def collection_media_list(user_mc_key, tags_id):
    more_media = True
    all_media = []
    max_media_id = 0
    while more_media:
        logger.debug("last_media_id %s", str(max_media_id))
        media = collection_media_list_page(user_mc_key, tags_id, max_media_id)
        all_media = all_media + media
        if len(media) > 0:
            max_media_id = media[len(media) - 1]['media_id']
        more_media = len(media) != 0
    return sorted(all_media, key=lambda t: t['name'])


def collection_media_list_page(user_mc_key, tags_id, max_media_id):
    '''
    We have to do this on the page, not the full list because memcache has a 1MB cache upper limit,
    and some of the collections have TONS of sources
    '''
    user_mc = user_mediacloud_client()
    return user_mc.mediaList(tags_id=tags_id, last_media_id=max_media_id, rows=100)


@app.route('/api/collections/<collection_id>/sentences/count', methods=['GET'])
@flask_login.login_required
@api_error_handler
def api_collection_sentence_count(collection_id):
    info = {}
    info['sentenceCounts'] = cached_recent_sentence_counts(user_mediacloud_key(),
                                                           ['tags_id_media:' + str(collection_id)])
    return jsonify({'results': info})


@app.route('/api/collections/<collection_id>/sentences/sentence-count.csv', methods=['GET'])
@flask_login.login_required
@api_error_handler
def collection_sentence_count_csv(collection_id):
    return stream_sentence_count_csv(user_mediacloud_key(), 'sentenceCounts-Collection-' + collection_id, collection_id,
                                     "tags_id_media")


@app.route('/api/collections/<collection_id>/geography')
@flask_login.login_required
@api_error_handler
def geo_geography(collection_id):
    info = {}
    info['geography'] = cached_geotag_count(user_mediacloud_key(), 'tags_id_media:' + str(collection_id))
    return jsonify({'results': info})


@app.route('/api/collections/<collection_id>/geography/geography.csv')
@flask_login.login_required
@api_error_handler
def collection_geo_csv(collection_id):
    return stream_geo_csv(user_mediacloud_key(), 'geography-Collection-' + collection_id, collection_id,
                          "tags_id_media")


@app.route('/api/collections/<collection_id>/words')
@flask_login.login_required
@api_error_handler
def collection_words(collection_id):
    info = {
        'wordcounts': cached_wordcount(user_mediacloud_key, 'tags_id_media:' + str(collection_id))
    }
    return jsonify({'results': info})


@app.route('/api/collections/<collection_id>/words/wordcount.csv', methods=['GET'])
@flask_login.login_required
@api_error_handler
def collection_wordcount_csv(collection_id):
    return stream_wordcount_csv(user_mediacloud_key(), 'wordcounts-Collection-' + collection_id, collection_id,
                                "tags_id_media")


@app.route('/api/collections/<collection_id>/similarCollections', methods=['GET'])
@flask_login.login_required
@api_error_handler
def similarCollections(collection_id):
    info = {}
    info['similarCollections'] = mc.tagList(similar_tags_id=collection_id)
    return jsonify({'results': info})


@app.route('/api/collections/create', methods=['POST'])
@form_fields_required('name', 'description')
@flask_login.login_required
@api_error_handler
def collection_create():
    user_mc = user_mediacloud_client()
    name = request.form['name']
    description = request.form['description']
    static = request.form['static'] if 'static' in request.form else None
    show_on_stories = request.form['showOnStories'] if 'showOnStories' in request.form else None
    show_on_media = request.form['showOnMedia'] if 'showOnMedia' in request.form else None
    source_ids = []
    if len(request.form['sources[]']) > 0:
        source_ids = request.form['sources[]'].split(',')
    # first create the collection
    new_collection = user_mc.createTag(COLLECTIONS_TAG_SET_ID, name, name, description,
                                       is_static=(static == 'true'),
                                       show_on_stories=(show_on_stories == 'true'),
                                       show_on_media=(show_on_media == 'true'))
    # then go through and tag all the sources specified with the new collection id
    tags = [MediaTag(sid, tags_id=new_collection['tag']['tags_id'], action=TAG_ACTION_ADD) for sid in source_ids]
    if len(tags) > 0:
        user_mc.tagMedia(tags)
    return jsonify(new_collection['tag'])


@app.route('/api/collections/<collection_id>/update', methods=['POST'])
@form_fields_required('name', 'description')
@flask_login.login_required
@api_error_handler
def collection_update(collection_id):
    user_mc = user_mediacloud_client()
    name = request.form['name']
    description = request.form['description']
    static = request.form['static'] if 'static' in request.form else None
    show_on_stories = request.form['showOnStories'] if 'showOnStories' in request.form else None
    show_on_media = request.form['showOnMedia'] if 'showOnMedia' in request.form else None
    source_ids = []
    if len(request.form['sources[]']) > 0:
        source_ids = [sid for sid in request.form['sources[]'].split(',')]
    # first update the collection
    updated_collection = user_mc.updateTag(collection_id, name, name, description,
                                           is_static=(static == 'true'),
                                           show_on_stories=(show_on_stories == 'true'),
                                           show_on_media=(show_on_media == 'true'))
    # get the sources in the collection first, then remove and add as needed
    existing_source_ids = [m['media_id'] for m in collection_media_list(user_mediacloud_key(), collection_id)]
    source_ids_to_remove = list(set(existing_source_ids) - set(source_ids))
    source_ids_to_add = [sid for sid in source_ids if sid not in existing_source_ids]
    logger.debug(existing_source_ids)
    logger.debug(source_ids_to_add)
    logger.debug(source_ids_to_remove)
    # then go through and tag all the sources specified with the new collection id
    tags_to_add = [MediaTag(sid, tags_id=collection_id, action=TAG_ACTION_ADD) for sid in source_ids_to_add]
    tags_to_remove = [MediaTag(sid, tags_id=collection_id, action=TAG_ACTION_REMOVE) for sid in source_ids_to_remove]
    tags = tags_to_add + tags_to_remove
    if len(tags) > 0:
        user_mc.tagMedia(tags)
    return jsonify(updated_collection['tag'])
