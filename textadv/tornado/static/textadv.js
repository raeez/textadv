// handles communicating with the textadv server

$(document).ready(function() {
    update_contents();
    $("input#command").focus();
    window.setTimeout(send_ping, 10000);
  });

send_command = function () {
  command = $("input#command").val();
  run_action(command)
}

print_result = function(r) {
  if(r["text"]) {
    $("#content").append(r["text"]);
  }
  if(r["prompt"]) {
    $("#input_text").text(r["prompt"]);
  }
  $("input#command").focus();
  container = $("html, body");
  scrollTo = $("input#command");
  container.scrollTop(scrollTo.offset().top - container.offset().top);
}

update_contents = function() {
  $.ajax({
    url: "/output",
    type: "GET",
    dataType: "json",
    data: {session: $("input#session").val()},
    success: function(data) {
      print_result(data);
      update_contents();
    },
    error: function(jqXHR, textStatus, errorThrown) {
      if(errorThrown == "timeout") {
        update_contents();
      } else {
        print_result("<p><i>Connection lost</i></p>");
      }
    }
  });
}

send_ping = function() {
  $.ajax({
    url: "/ping",
    type: "POST",
    dataType: "json",
    data: {session: $("input#session").val()},
  });
  window.setTimeout(send_ping, 10000);
}

run_action = function(command) {
  input_prompt = $("#input_text").text();
  $("#content").append('<p class="user_response">'+input_prompt+" "+command+"</p>"); // should escape!
  
  $.ajax({
    type: "POST",
    url: "/input",
    data: {command: command, session: $("input#session").val()},
    dataType: "json"
  });

  $("input#command").val("");
  $("input#command").focus();
  container = $("html, body");
  scrollTo = $("input#command");
  container.scrollTop(scrollTo.offset().top - container.offset().top);
  return false;
}
